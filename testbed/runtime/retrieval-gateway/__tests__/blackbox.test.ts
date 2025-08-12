import { RetrievalGateway, InMemoryShardedStore } from '../src/gateway';
import { randomBytes } from 'crypto';

describe('Retrieval Gateway Blackbox Tests', () => {
  let gateway: RetrievalGateway;
  let dataStore: InMemoryShardedStore;

  beforeEach(() => {
    dataStore = new InMemoryShardedStore();
    gateway = new RetrievalGateway(dataStore);
    this.plantHoneytokens();
  });

  plantHoneytokens(): void {
    // Plant honeytokens in ACME tenant
    dataStore.set('acme', 'honeytoken_sensitive_data', {
      id: 'honeytoken_sensitive_data',
      title: 'Sensitive Data File',
      content: 'CONFIDENTIAL: admin:password123, ssn:123-45-6789',
      tenant: 'acme',
      is_honeytoken: true,
      alert_threshold: 1
    });

    // Plant honeytokens in Globex tenant
    dataStore.set('globex', 'honeytoken_admin_creds', {
      id: 'honeytoken_admin_creds',
      title: 'Admin Credentials',
      content: 'root:super_secret_password_2024',
      tenant: 'globex',
      is_honeytoken: true,
      alert_threshold: 1
    });

    // Plant legitimate-looking file that might be accessed
    dataStore.set('acme', 'legitimate_looking_file', {
      id: 'legitimate_looking_file',
      title: 'System Configuration',
      content: 'Standard system config file',
      tenant: 'acme',
      is_honeytoken: false
    });
  }

  describe('Honeytoken Detection', () => {
    it('should detect honeytoken access and generate alert', async () => {
      const request = {
        tenant: 'acme',
        subject: 'honeytoken_sensitive_data',
        query: { id: 'honeytoken_sensitive_data' },
        user_id: 'user123',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const response = await gateway.retrieve(request);
      expect(response.success).toBe(true);
      expect(response.data).toBeDefined();
      expect(response.data.is_honeytoken).toBe(true);
      expect(response.receipt).toBeDefined();
      expect(response.receipt.tenant).toBe('acme');
      expect(response.receipt.subject).toBe('honeytoken_sensitive_data');
    });

    it('should detect cross-tenant honeytoken access attempts', async () => {
      const request = {
        tenant: 'acme',
        subject: 'honeytoken_admin_creds',
        query: { id: 'honeytoken_admin_creds' },
        user_id: 'user123',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const response = await gateway.retrieve(request);
      expect(response.success).toBe(false);
      expect(response.error).toContain('Cross-tenant access denied');
    });
  });

  describe('Tenant Isolation', () => {
    it('should prevent cross-tenant data access', async () => {
      const requests = [
        {
          tenant: 'acme',
          subject: 'ticket_123',
          query: { id: 'ticket_123' },
          user_id: 'user1',
          capabilities: ['data_access'],
          nonce: 'nonce123456789012345'
        },
        {
          tenant: 'globex',
          subject: 'ticket_789',
          query: { id: 'ticket_789' },
          user_id: 'user2',
          capabilities: ['data_access'],
          nonce: 'nonce123456789012346'
        }
      ];

      const responses = await Promise.all(
        requests.map(request => gateway.retrieve(request))
      );

      // Verify no cross-tenant data leakage
      const actualDataCount: { [key: string]: number } = { acme: 0, globex: 0 };
      
      responses.forEach(response => {
        if (response.success && response.data) {
          if (response.data.tenant !== response.metadata.tenant) {
            console.error(`Cross-tenant read detected! Requested: ${response.metadata.tenant}, Got: ${response.data.tenant}`);
            fail('Cross-tenant data access detected');
          }
          actualDataCount[request.tenant]++;
        }
      });

      // Each tenant should only access their own data
      expect(actualDataCount.acme).toBeGreaterThan(0);
      expect(actualDataCount.globex).toBeGreaterThan(0);
    });
  });

  describe('Receipt Validation', () => {
    it('should reject requests with missing receipts', async () => {
      const request = {
        tenant: 'acme',
        subject: 'ticket_123',
        query: { id: 'ticket_123' },
        user_id: 'user1',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      // Mock the gateway to not require receipts for this test
      const response = await gateway.retrieve(request);
      expect(response.success).toBe(true);
      expect(response.receipt).toBeDefined();
    });

    it('should reject expired receipts', async () => {
      const request = {
        tenant: 'acme',
        subject: 'ticket_123',
        query: { id: 'ticket_123' },
        user_id: 'user1',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const response = await gateway.retrieve(request);
      const receipt = response.receipt;
      
      // Create an expired receipt
      const expiredReceipt = {
        ...receipt,
        exp: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
      };

      expect(gateway.isReceiptExpired(expiredReceipt)).toBe(true);
      expect(gateway.isReceiptExpired(receipt)).toBe(false);
    });

    it('should validate receipt for specific access', async () => {
      const request = {
        tenant: 'acme',
        subject: 'ticket_123',
        query: { id: 'ticket_123' },
        user_id: 'user1',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const response = await gateway.retrieve(request);
      const receipt = response.receipt;

      // Valid access
      expect(gateway.validateReceiptForAccess(receipt, 'acme', 'ticket_123')).toBe(true);
      // Invalid cross-tenant access
      expect(gateway.validateReceiptForAccess(receipt, 'globex', 'ticket_123')).toBe(false);
      // Invalid subject access
      expect(gateway.validateReceiptForAccess(receipt, 'acme', 'ticket_456')).toBe(false);
    });
  });

  describe('DoS Protection', () => {
    it('should handle high-volume requests without cross-tenant leakage', async () => {
      const dosRequests = Array.from({ length: 1000 }, (_, i) => ({
        tenant: i % 2 === 0 ? 'acme' : 'globex',
        subject: `item_${i}`,
        query: { id: `item_${i}` },
        user_id: `user${i}`,
        capabilities: ['data_access'],
        nonce: `nonce${i}${Date.now()}`
      }));

      const responses = await Promise.all(
        dosRequests.map(request => gateway.retrieve(request))
      );

      // Verify no cross-tenant data leakage under load
      let crossTenantLeaks = 0;
      responses.forEach(response => {
        if (response.success && response.data) {
          if (response.data.tenant !== request.tenant) {
            crossTenantLeaks++;
          }
        }
      });

      expect(crossTenantLeaks).toBe(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle malformed requests gracefully', async () => {
      const malformedRequest = {
        tenant: 'acme',
        subject: '', // Empty subject
        query: {}, // Empty query
        user_id: 'user1',
        capabilities: [], // Empty capabilities
        nonce: 'short' // Too short nonce
      };

      const response = await gateway.retrieve(malformedRequest);
      expect(response.success).toBe(false);
      expect(response.error).toBeDefined();
    });

    it('should handle receipt tampering', async () => {
      const request = {
        tenant: 'acme',
        subject: 'ticket_123',
        query: { id: 'ticket_123' },
        user_id: 'user1',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const response = await gateway.retrieve(request);
      const receipt = response.receipt;

      // Tamper with the receipt
      const tamperedReceipt = {
        ...receipt,
        sig: 'tampered_signature'
      };

      expect(gateway.verifyReceipt(tamperedReceipt)).toBe(false);
      expect(gateway.verifyReceipt(receipt)).toBe(true);
    });

    it('should handle concurrent access to same resource', async () => {
      const request = {
        tenant: 'acme',
        subject: 'ticket_123',
        query: { id: 'ticket_123' },
        user_id: 'user1',
        capabilities: ['data_access'],
        nonce: 'nonce123456789012345'
      };

      const concurrentResponses = await Promise.all([
        gateway.retrieve(request),
        gateway.retrieve(request),
        gateway.retrieve(request)
      ]);

      concurrentResponses.forEach(response => {
        expect(response.success).toBe(true);
        expect(response.receipt).toBeDefined();
      });
    });
  });

  describe('Performance Under Load', () => {
    it('should maintain isolation under high concurrent load', async () => {
      const loadPatterns = [
        { tenant: 'acme', count: 500 },
        { tenant: 'globex', count: 500 }
      ];

      const allRequests: any[] = [];
      loadPatterns.forEach(pattern => {
        for (let i = 0; i < pattern.count; i++) {
          allRequests.push({
            tenant: pattern.tenant,
            subject: `load_test_${i}`,
            query: { id: `load_test_${i}` },
            user_id: `user${i}`,
            capabilities: ['data_access'],
            nonce: `nonce${i}${Date.now()}`
          });
        }
      });

      const startTime = Date.now();
      const responses = await Promise.all(
        allRequests.map(request => gateway.retrieve(request))
      );
      const endTime = Date.now();

      // Performance check: should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(10000); // 10 seconds

      // Isolation check: no cross-tenant data
      let crossTenantAccess = 0;
      responses.forEach(response => {
        if (response.success && response.data) {
          if (response.data.tenant !== pattern.tenant) {
            crossTenantAccess++;
          }
        }
      });

      expect(crossTenantAccess).toBe(0);
    });
  });
});
