import { ABACRequest, ABACResponse } from './types';
export declare class ABACEngine {
    private policies;
    private tenantContexts;
    constructor();
    private initializeDefaultPolicies;
    evaluateAccess(request: ABACRequest): Promise<ABACResponse>;
    private generateLabelsForRole;
    private generateMockResults;
    private generateMockData;
    private determineAccessLevel;
}
//# sourceMappingURL=abac-engine.d.ts.map