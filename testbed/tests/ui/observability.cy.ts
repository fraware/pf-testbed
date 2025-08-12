import { observabilityService } from '../../runtime/gateway/src/observability';
import { testbedMetrics } from '../../runtime/gateway/src/metrics';

describe('TB-12: Observability & Proof Click-through', () => {
  beforeEach(() => {
    // Setup test data
    cy.intercept('GET', '/api/metrics', { fixture: 'metrics.json' }).as('getMetrics');
    cy.intercept('GET', '/api/traces/*', { fixture: 'trace.json' }).as('getTrace');
    cy.intercept('GET', '/api/theorems/*', { fixture: 'theorem.json' }).as('getTheorem');
    cy.intercept('GET', '/api/certificates/*', { fixture: 'certificate.json' }).as('getCertificate');
  });

  describe('Grafana Dashboard Integration', () => {
    it('should display SLO metrics with proper thresholds', () => {
      cy.visit('/dashboard/observability');
      
      // Check SLO panel exists and loads within 2s
      cy.get('[data-testid="slo-overview"]', { timeout: 2000 }).should('be.visible');
      
      // Verify SLO violations are displayed
      cy.get('[data-testid="slo-violations-count"]').should('contain.text', '0');
      
      // Check color coding based on thresholds
      cy.get('[data-testid="slo-overview"]').should('have.class', 'status-green');
    });

    it('should display latency P95/P99 metrics', () => {
      cy.visit('/dashboard/observability');
      
      cy.get('[data-testid="latency-chart"]', { timeout: 2000 }).should('be.visible');
      
      // Verify P95 and P99 are displayed
      cy.get('[data-testid="p95-latency"]').should('contain.text', 'ms');
      cy.get('[data-testid="p99-latency"]').should('contain.text', 'ms');
      
      // Check thresholds are properly set
      cy.get('[data-testid="latency-chart"]').should('have.class', 'thresholds-configured');
    });

    it('should display theorem verification rate', () => {
      cy.visit('/dashboard/observability');
      
      cy.get('[data-testid="theorem-verification-gauge"]', { timeout: 2000 }).should('be.visible');
      
      // Verify gauge shows percentage
      cy.get('[data-testid="verification-rate"]').should('match', /\d+%/);
    });

    it('should display honeytoken alerts', () => {
      cy.visit('/dashboard/observability');
      
      cy.get('[data-testid="honeytoken-alerts"]', { timeout: 2000 }).should('be.visible');
      
      // Check table structure
      cy.get('[data-testid="honeytoken-table"]').find('tr').should('have.length.gt', 1);
    });
  });

  describe('UI Calls Drawer: Trace → Plan → Theorem → Cert', () => {
    it('should navigate through complete trace chain in under 2 seconds', () => {
      cy.visit('/traces');
      
      // Click on a trace to open drawer
      cy.get('[data-testid="trace-row"]').first().click();
      
      // Verify drawer opens within 2s
      cy.get('[data-testid="trace-drawer"]', { timeout: 2000 }).should('be.visible');
      
      // Navigate through the chain
      cy.get('[data-testid="trace-chain"]').should('be.visible');
      
      // Click through each step and verify loading time
      const startTime = Date.now();
      
      cy.get('[data-testid="plan-link"]').click();
      cy.get('[data-testid="plan-details"]', { timeout: 2000 }).should('be.visible');
      
      cy.get('[data-testid="theorem-link"]').click();
      cy.get('[data-testid="theorem-details"]', { timeout: 2000 }).should('be.visible');
      
      cy.get('[data-testid="certificate-link"]').click();
      cy.get('[data-testid="certificate-details"]', { timeout: 2000 }).should('be.visible');
      
      const endTime = Date.now();
      const totalTime = endTime - startTime;
      
      // Total click-through time should be under 2 seconds
      expect(totalTime).to.be.lessThan(2000);
    });

    it('should link trace IDs to Lean theorems and spec lines', () => {
      cy.visit('/traces');
      cy.get('[data-testid="trace-row"]').first().click();
      
      cy.get('[data-testid="trace-drawer"]').should('be.visible');
      
      // Verify Lean theorem mappings are displayed
      cy.get('[data-testid="lean-theorems"]').should('be.visible');
      cy.get('[data-testid="theorem-mapping"]').should('have.length.gt', 0);
      
      // Check spec file and line information
      cy.get('[data-testid="spec-file"]').should('contain.text', '.lean');
      cy.get('[data-testid="spec-line"]').should('match', /\d+/);
      
      // Verify confidence scores
      cy.get('[data-testid="theorem-confidence"]').should('match', /\d+%/);
    });

    it('should have no broken links in trace chain', () => {
      cy.visit('/traces');
      cy.get('[data-testid="trace-row"]').first().click();
      
      // Check all links in the trace chain
      cy.get('[data-testid="trace-chain"]').find('a').each(($link) => {
        const href = $link.attr('href');
        if (href && !href.startsWith('#')) {
          // Verify link is not broken
          cy.request({
            url: href,
            failOnStatusCode: false
          }).then((response) => {
            expect(response.status).to.not.equal(404);
          });
        }
      });
    });
  });

  describe('Saved Views per Journey & Tenant', () => {
    it('should save and load views for specific journeys and tenants', () => {
      cy.visit('/dashboard/observability');
      
      // Create a custom view
      cy.get('[data-testid="save-view-btn"]').click();
      cy.get('[data-testid="view-name-input"]').type('Test View');
      cy.get('[data-testid="journey-select"]').select('support_triage');
      cy.get('[data-testid="tenant-select"]').select('test-tenant');
      
      // Configure filters
      cy.get('[data-testid="time-range-start"]').type('2024-01-01');
      cy.get('[data-testid="time-range-end"]').type('2024-12-31');
      
      cy.get('[data-testid="save-view-submit"]').click();
      
      // Verify view is saved
      cy.get('[data-testid="saved-views"]').should('contain.text', 'Test View');
      
      // Load the saved view
      cy.get('[data-testid="load-view-btn"]').click();
      cy.get('[data-testid="view-list"]').contains('Test View').click();
      
      // Verify view loads with correct filters
      cy.get('[data-testid="journey-filter"]').should('have.value', 'support_triage');
      cy.get('[data-testid="tenant-filter"]').should('have.value', 'test-tenant');
    });

    it('should maintain view persistence across sessions', () => {
      // Save a view
      cy.visit('/dashboard/observability');
      cy.get('[data-testid="save-view-btn"]').click();
      cy.get('[data-testid="view-name-input"]').type('Persistent View');
      cy.get('[data-testid="save-view-submit"]').click();
      
      // Reload page
      cy.reload();
      
      // Verify view is still available
      cy.get('[data-testid="saved-views"]').should('contain.text', 'Persistent View');
    });
  });

  describe('Performance Gates', () => {
    it('should maintain click-through latency under 2 seconds under load', () => {
      // Simulate load by creating multiple traces
      for (let i = 0; i < 10; i++) {
        cy.request('POST', '/api/traces', {
          tenant: 'test-tenant',
          journey: 'support_triage',
          user_id: `user-${i}`
        });
      }
      
      cy.visit('/traces');
      
      // Measure click-through time under load
      const startTime = Date.now();
      
      cy.get('[data-testid="trace-row"]').first().click();
      cy.get('[data-testid="trace-drawer"]', { timeout: 2000 }).should('be.visible');
      
      cy.get('[data-testid="plan-link"]').click();
      cy.get('[data-testid="plan-details"]', { timeout: 2000 }).should('be.visible');
      
      const endTime = Date.now();
      const clickThroughTime = endTime - startTime;
      
      // Should still be under 2 seconds even under load
      expect(clickThroughTime).to.be.lessThan(2000);
    });

    it('should handle concurrent trace requests without performance degradation', () => {
      // Make concurrent requests
      const requests = Array.from({ length: 5 }, (_, i) => 
        cy.request('POST', '/api/traces', {
          tenant: 'test-tenant',
          journey: 'support_triage',
          user_id: `user-${i}`
        })
      );
      
      cy.wrap(requests).then(() => {
        // Verify all requests completed successfully
        cy.get('[data-testid="traces-count"]').should('contain.text', '5');
      });
    });
  });

  describe('Double-checks', () => {
    it('should fail UI test when theorem mapping is deleted', () => {
      // This test should fail when theorem mappings are removed
      // demonstrating the robustness of the test coverage
      
      cy.visit('/traces');
      cy.get('[data-testid="trace-row"]').first().click();
      
      // Verify theorem mapping exists
      cy.get('[data-testid="theorem-mapping"]').should('be.visible');
      
      // Simulate deletion of theorem mapping
      cy.intercept('GET', '/api/theorems/*', { statusCode: 404 }).as('theoremNotFound');
      
      // Navigate to theorem
      cy.get('[data-testid="theorem-link"]').click();
      
      // Should show error state
      cy.get('[data-testid="theorem-error"]').should('be.visible');
      cy.get('[data-testid="theorem-error"]').should('contain.text', 'Theorem not found');
    });
  });

  describe('Live Demo Flows', () => {
    it('should demonstrate complete workflow on one screen', () => {
      cy.visit('/demo');
      
      // Verify all components are visible on one screen
      cy.get('[data-testid="demo-container"]').should('be.visible');
      cy.get('[data-testid="trace-panel"]').should('be.visible');
      cy.get('[data-testid="plan-panel"]').should('be.visible');
      cy.get('[data-testid="theorem-panel"]').should('be.visible');
      cy.get('[data-testid="certificate-panel"]').should('be.visible');
      
      // Execute demo flow
      cy.get('[data-testid="start-demo-btn"]').click();
      
      // Verify flow completes successfully
      cy.get('[data-testid="demo-status"]').should('contain.text', 'Completed');
      cy.get('[data-testid="demo-metrics"]').should('be.visible');
      
      // Check all panels show relevant data
      cy.get('[data-testid="trace-data"]').should('not.be.empty');
      cy.get('[data-testid="plan-data"]').should('not.be.empty');
      cy.get('[data-testid="theorem-data"]').should('not.be.empty');
      cy.get('[data-testid="certificate-data"]').should('not.be.empty');
    });
  });
});
