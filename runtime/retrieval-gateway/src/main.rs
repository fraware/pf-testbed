use actix_web::App;
use std::collections::HashMap;
use std::env;
use ed25519_dalek::Keypair;
use rand::thread_rng;

mod gateway;

use gateway::{RetrievalGateway, GatewayConfig};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize logging
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    
    // Load configuration from environment variables
    let host = env::var("GATEWAY_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = env::var("GATEWAY_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse::<u16>()
        .expect("Invalid port number");
    
    let max_query_size = env::var("MAX_QUERY_SIZE")
        .unwrap_or_else(|_| "10000".to_string())
        .parse::<usize>()
        .expect("Invalid max query size");
    
    let query_timeout_ms = env::var("QUERY_TIMEOUT_MS")
        .unwrap_or_else(|_| "5000".to_string())
        .parse::<u64>()
        .expect("Invalid query timeout");
    
    // Generate signing key (in production, load from secure storage)
    let signing_key = Keypair::generate(&mut thread_rng());
    
    // Configure tenant shards
    let mut tenant_shards = HashMap::new();
    tenant_shards.insert("acme".to_string(), "acme-shard-1".to_string());
    tenant_shards.insert("globex".to_string(), "globex-shard-1".to_string());
    
    // Create gateway configuration
    let config = GatewayConfig {
        host,
        port,
        signing_key,
        tenant_shards,
        max_query_size,
        query_timeout_ms,
    };
    
    log::info!("Starting Retrieval Gateway on {}:{}", config.host, config.port);
    log::info!("Max query size: {} bytes", config.max_query_size);
    log::info!("Query timeout: {} ms", config.query_timeout_ms);
    log::info!("Tenant shards: {:?}", config.tenant_shards);
    
    // Create and start the gateway
    let gateway = RetrievalGateway::new(config);
    gateway.start().await
}
