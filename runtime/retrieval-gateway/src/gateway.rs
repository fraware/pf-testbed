use actix_web::{web, App, HttpServer, HttpResponse, HttpRequest, Error};
use actix_web::middleware::Logger;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use sha2::{Sha256, Digest};
use ed25519_dalek::{Keypair, PublicKey, SecretKey, Signature, Verifier};
use base64::{Engine as _, engine::general_purpose};

/// Configuration for the Retrieval Gateway
#[derive(Clone, Debug)]
pub struct GatewayConfig {
    pub host: String,
    pub port: u16,
    pub signing_key: Keypair,
    pub tenant_shards: HashMap<String, String>,
    pub max_query_size: usize,
    pub query_timeout_ms: u64,
}

/// Access Receipt for data retrieval operations
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AccessReceipt {
    pub id: String,
    pub tenant: String,
    pub subject: String,
    pub shard: String,
    pub query_hash: String,
    pub result_hash: String,
    pub nonce: String,
    pub expires_at: DateTime<Utc>,
    pub signature: String,
}

/// Query request from clients
#[derive(Debug, Deserialize)]
pub struct QueryRequest {
    pub tenant: String,
    pub query: String,
    pub filters: Option<HashMap<String, Value>>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
}

/// Query response with receipt
#[derive(Debug, Serialize)]
pub struct QueryResponse {
    pub success: bool,
    pub data: Option<Vec<Value>>,
    pub receipt: AccessReceipt,
    pub metadata: QueryMetadata,
}

/// Query metadata
#[derive(Debug, Serialize)]
pub struct QueryMetadata {
    pub query_id: String,
    pub execution_time_ms: u64,
    pub result_count: usize,
    pub shard: String,
    pub timestamp: DateTime<Utc>,
}

/// Error response
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub code: String,
    pub details: Option<Value>,
}

/// Retrieval Gateway implementation
pub struct RetrievalGateway {
    config: GatewayConfig,
    nonce_cache: Arc<Mutex<HashMap<String, DateTime<Utc>>>,
    query_log: Arc<Mutex<Vec<QueryLogEntry>>>,
}

/// Query log entry for audit trail
#[derive(Debug, Clone)]
struct QueryLogEntry {
    pub id: String,
    pub tenant: String,
    pub query: String,
    pub timestamp: DateTime<Utc>,
    pub receipt_id: String,
    pub success: bool,
    pub error: Option<String>,
}

impl RetrievalGateway {
    /// Create a new Retrieval Gateway instance
    pub fn new(config: GatewayConfig) -> Self {
        Self {
            config,
            nonce_cache: Arc::new(Mutex::new(HashMap::new())),
            query_log: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Start the HTTP server
    pub async fn start(self) -> std::io::Result<()> {
        let gateway = web::Data::new(self);
        
        HttpServer::new(move || {
            App::new()
                .app_data(gateway.clone())
                .wrap(Logger::default())
                .service(
                    web::scope("/api/v1")
                        .route("/query", web::post().to(Self::handle_query))
                        .route("/receipt/{id}/verify", web::get().to(Self::verify_receipt))
                        .route("/health", web::get().to(Self::health_check))
                        .route("/stats", web::get().to(Self::get_stats))
                )
        })
        .bind(format!("{}:{}", self.config.host, self.config.port))?
        .run()
        .await
    }

    /// Handle query requests
    async fn handle_query(
        req: HttpRequest,
        payload: web::Json<QueryRequest>,
        gateway: web::Data<Self>,
    ) -> Result<HttpResponse, Error> {
        let start_time = std::time::Instant::now();
        
        // Validate request
        if let Err(e) = gateway.validate_query_request(&payload) {
            return Ok(HttpResponse::BadRequest().json(ErrorResponse {
                error: e,
                code: "INVALID_REQUEST".to_string(),
                details: None,
            }));
        }

        // Check tenant isolation
        if let Err(e) = gateway.check_tenant_isolation(&req, &payload.tenant) {
            return Ok(HttpResponse::Forbidden().json(ErrorResponse {
                error: e,
                code: "TENANT_ISOLATION_VIOLATION".to_string(),
                details: None,
            }));
        }

        // Execute query
        let query_result = gateway.execute_query(&payload).await;
        
        let execution_time = start_time.elapsed().as_millis() as u64;
        
        match query_result {
            Ok(data) => {
                // Generate access receipt
                let receipt = gateway.generate_access_receipt(&payload, &data, execution_time);
                
                // Log query
                gateway.log_query(&payload, &receipt, true, None, execution_time);
                
                // Return response with receipt
                let response = QueryResponse {
                    success: true,
                    data: Some(data),
                    receipt,
                    metadata: QueryMetadata {
                        query_id: Uuid::new_v4().to_string(),
                        execution_time_ms: execution_time,
                        result_count: data.len(),
                        shard: gateway.get_shard_for_tenant(&payload.tenant),
                        timestamp: Utc::now(),
                    },
                };
                
                Ok(HttpResponse::Ok().json(response))
            }
            Err(e) => {
                // Log failed query
                let receipt = gateway.generate_error_receipt(&payload, &e);
                gateway.log_query(&payload, &receipt, false, Some(&e), execution_time);
                
                Ok(HttpResponse::InternalServerError().json(ErrorResponse {
                    error: e,
                    code: "QUERY_EXECUTION_FAILED".to_string(),
                    details: None,
                }))
            }
        }
    }

    /// Verify an access receipt
    async fn verify_receipt(
        path: web::Path<String>,
        gateway: web::Data<Self>,
    ) -> Result<HttpResponse, Error> {
        let receipt_id = path.into_inner();
        
        match gateway.verify_receipt_signature(&receipt_id) {
            Ok(receipt) => {
                // Check if receipt is expired
                if receipt.expires_at < Utc::now() {
                    return Ok(HttpResponse::Gone().json(ErrorResponse {
                        error: "Receipt has expired".to_string(),
                        code: "RECEIPT_EXPIRED".to_string(),
                        details: None,
                    }));
                }
                
                // Check if nonce has been used (replay protection)
                if gateway.is_nonce_used(&receipt.nonce) {
                    return Ok(HttpResponse::Conflict().json(ErrorResponse {
                        error: "Receipt nonce already used".to_string(),
                        code: "RECEIPT_REPLAY".to_string(),
                        details: None,
                    }));
                }
                
                // Mark nonce as used
                gateway.mark_nonce_used(&receipt.nonce);
                
                Ok(HttpResponse::Ok().json(receipt))
            }
            Err(e) => {
                Ok(HttpResponse::Unauthorized().json(ErrorResponse {
                    error: e,
                    code: "INVALID_SIGNATURE".to_string(),
                    details: None,
                }))
            }
        }
    }

    /// Health check endpoint
    async fn health_check() -> HttpResponse {
        HttpResponse::Ok().json(serde_json::json!({
            "status": "healthy",
            "timestamp": Utc::now().to_rfc3339(),
            "service": "retrieval-gateway"
        }))
    }

    /// Get gateway statistics
    async fn get_stats(gateway: web::Data<Self>) -> HttpResponse {
        let stats = gateway.get_statistics();
        HttpResponse::Ok().json(stats)
    }

    /// Validate query request
    fn validate_query_request(&self, req: &QueryRequest) -> Result<(), String> {
        if req.tenant.is_empty() {
            return Err("Tenant is required".to_string());
        }
        
        if req.query.is_empty() {
            return Err("Query is required".to_string());
        }
        
        if req.query.len() > self.config.max_query_size {
            return Err("Query too long".to_string());
        }
        
        if let Some(limit) = req.limit {
            if limit > 1000 {
                return Err("Limit too high".to_string());
            }
        }
        
        Ok(())
    }

    /// Check tenant isolation
    fn check_tenant_isolation(&self, req: &HttpRequest, tenant: &str) -> Result<(), String> {
        // Extract tenant from request headers or JWT token
        let request_tenant = self.extract_tenant_from_request(req);
        
        if request_tenant != tenant {
            return Err("Tenant mismatch in request".to_string());
        }
        
        // Check if tenant has access to the requested shard
        let shard = self.get_shard_for_tenant(tenant);
        if !self.config.tenant_shards.contains_key(tenant) {
            return Err("Tenant not found".to_string());
        }
        
        Ok(())
    }

    /// Execute a query against the data store
    async fn execute_query(&self, req: &QueryRequest) -> Result<Vec<Value>, String> {
        // This is a simplified implementation
        // In a real system, you would:
        // 1. Parse and validate the query
        // 2. Check capabilities and permissions
        // 3. Execute against the appropriate data store
        // 4. Apply filters and pagination
        // 5. Return results
        
        // Simulate query execution
        tokio::time::sleep(tokio::time::Duration::from_millis(
            self.config.query_timeout_ms
        )).await;
        
        // Return mock data for now
        Ok(vec![
            serde_json::json!({
                "id": "doc_1",
                "tenant": req.tenant,
                "content": "Sample document content",
                "labels": {
                    "pii": "masked",
                    "sensitivity": "medium"
                }
            })
        ])
    }

    /// Generate an access receipt for a successful query
    fn generate_access_receipt(
        &self,
        req: &QueryRequest,
        data: &[Value],
        execution_time: u64,
    ) -> AccessReceipt {
        let query_hash = self.hash_query(&req.query);
        let result_hash = self.hash_results(data);
        let nonce = Uuid::new_v4().to_string();
        let expires_at = Utc::now() + chrono::Duration::hours(24);
        
        let receipt = AccessReceipt {
            id: Uuid::new_v4().to_string(),
            tenant: req.tenant.clone(),
            subject: "data_retrieval".to_string(),
            shard: self.get_shard_for_tenant(&req.tenant),
            query_hash,
            result_hash,
            nonce,
            expires_at,
            signature: String::new(), // Will be set below
        };
        
        // Sign the receipt
        let signature = self.sign_receipt(&receipt);
        AccessReceipt {
            signature,
            ..receipt
        }
    }

    /// Generate an error receipt for failed queries
    fn generate_error_receipt(&self, req: &QueryRequest, error: &str) -> AccessReceipt {
        let query_hash = self.hash_query(&req.query);
        let nonce = Uuid::new_v4().to_string();
        let expires_at = Utc::now() + chrono::Duration::hours(1);
        
        let receipt = AccessReceipt {
            id: Uuid::new_v4().to_string(),
            tenant: req.tenant.clone(),
            subject: "error".to_string(),
            shard: self.get_shard_for_tenant(&req.tenant),
            query_hash,
            result_hash: "".to_string(),
            nonce,
            expires_at,
            signature: String::new(),
        };
        
        // Sign the receipt
        let signature = self.sign_receipt(&receipt);
        AccessReceipt {
            signature,
            ..receipt
        }
    }

    /// Sign a receipt with the gateway's private key
    fn sign_receipt(&self, receipt: &AccessReceipt) -> String {
        let receipt_data = format!(
            "{}:{}:{}:{}:{}:{}:{}",
            receipt.id,
            receipt.tenant,
            receipt.subject,
            receipt.shard,
            receipt.query_hash,
            receipt.result_hash,
            receipt.nonce
        );
        
        let signature = self.config.signing_key.sign(receipt_data.as_bytes());
        general_purpose::STANDARD.encode(signature.to_bytes())
    }

    /// Verify a receipt signature
    fn verify_receipt_signature(&self, receipt_id: &str) -> Result<AccessReceipt, String> {
        // In a real implementation, you would:
        // 1. Retrieve the receipt from storage
        // 2. Verify the signature
        // 3. Return the receipt if valid
        
        // For now, return an error
        Err("Receipt verification not implemented".to_string())
    }

    /// Hash a query string
    fn hash_query(&self, query: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(query.as_bytes());
        general_purpose::STANDARD.encode(hasher.finalize())
    }

    /// Hash query results
    fn hash_results(&self, results: &[Value]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(serde_json::to_string(results).unwrap().as_bytes());
        general_purpose::STANDARD.encode(hasher.finalize())
    }

    /// Get the shard for a tenant
    fn get_shard_for_tenant(&self, tenant: &str) -> String {
        self.config.tenant_shards
            .get(tenant)
            .cloned()
            .unwrap_or_else(|| "default".to_string())
    }

    /// Extract tenant from request
    fn extract_tenant_from_request(&self, req: &HttpRequest) -> String {
        // In a real implementation, you would extract from JWT token or headers
        req.headers()
            .get("X-Tenant")
            .and_then(|h| h.to_str().ok())
            .unwrap_or("unknown")
            .to_string()
    }

    /// Check if a nonce has been used
    fn is_nonce_used(&self, nonce: &str) -> bool {
        let cache = self.nonce_cache.lock().unwrap();
        cache.contains_key(nonce)
    }

    /// Mark a nonce as used
    fn mark_nonce_used(&self, nonce: &str) {
        let mut cache = self.nonce_cache.lock().unwrap();
        cache.insert(nonce.to_string(), Utc::now());
    }

    /// Log a query for audit purposes
    fn log_query(
        &self,
        req: &QueryRequest,
        receipt: &AccessReceipt,
        success: bool,
        error: Option<&str>,
        execution_time: u64,
    ) {
        let entry = QueryLogEntry {
            id: Uuid::new_v4().to_string(),
            tenant: req.tenant.clone(),
            query: req.query.clone(),
            timestamp: Utc::now(),
            receipt_id: receipt.id.clone(),
            success,
            error: error.map(|e| e.to_string()),
        };
        
        let mut log = self.query_log.lock().unwrap();
        log.push(entry);
        
        // Keep only last 10000 entries
        if log.len() > 10000 {
            log.remove(0);
        }
    }

    /// Get gateway statistics
    fn get_statistics(&self) -> serde_json::Value {
        let log = self.query_log.lock().unwrap();
        let total_queries = log.len();
        let successful_queries = log.iter().filter(|e| e.success).count();
        let failed_queries = total_queries - successful_queries;
        
        serde_json::json!({
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": if total_queries > 0 {
                successful_queries as f64 / total_queries as f64
            } else {
                0.0
            },
            "uptime": "TODO: Implement uptime tracking",
            "timestamp": Utc::now().to_rfc3339()
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::Keypair;

    #[test]
    fn test_query_validation() {
        let config = GatewayConfig {
            host: "localhost".to_string(),
            port: 8080,
            signing_key: Keypair::generate(&mut rand::thread_rng()),
            tenant_shards: HashMap::new(),
            max_query_size: 1000,
            query_timeout_ms: 5000,
        };
        
        let gateway = RetrievalGateway::new(config);
        
        let valid_request = QueryRequest {
            tenant: "acme".to_string(),
            query: "SELECT * FROM employees".to_string(),
            filters: None,
            limit: Some(100),
            offset: Some(0),
        };
        
        assert!(gateway.validate_query_request(&valid_request).is_ok());
        
        let invalid_request = QueryRequest {
            tenant: "".to_string(),
            query: "SELECT * FROM employees".to_string(),
            filters: None,
            limit: None,
            offset: None,
        };
        
        assert!(gateway.validate_query_request(&invalid_request).is_err());
    }

    #[test]
    fn test_query_hashing() {
        let config = GatewayConfig {
            host: "localhost".to_string(),
            port: 8080,
            signing_key: Keypair::generate(&mut rand::thread_rng()),
            tenant_shards: HashMap::new(),
            max_query_size: 1000,
            query_timeout_ms: 5000,
        };
        
        let gateway = RetrievalGateway::new(config);
        
        let query1 = "SELECT * FROM employees";
        let query2 = "SELECT * FROM employees";
        let query3 = "SELECT * FROM customers";
        
        let hash1 = gateway.hash_query(query1);
        let hash2 = gateway.hash_query(query2);
        let hash3 = gateway.hash_query(query3);
        
        assert_eq!(hash1, hash2);
        assert_ne!(hash1, hash3);
    }
}
