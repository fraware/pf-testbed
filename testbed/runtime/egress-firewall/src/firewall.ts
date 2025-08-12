import { createHash } from 'crypto';
import { z } from 'zod';
import * as ed25519 from '@noble/ed25519';

// Egress Certificate Schema
export const EgressCertificateSchema = z.object({
  pii: z.enum(['detected', 'none', 'masked']),
  secrets: z.enum(['detected', 'none', 'masked']),
  near_dupe: z.enum(['detected', 'none']),
  non_interference: z.enum(['passed', 'failed']),
  influencing_labels: z.array(z.string()),
  policy_hash: z.string(),
  text_hash: z.string(),
  attestation_ref: z.string(),
  sig: z.string()
});

export type EgressCertificate = z.infer<typeof EgressCertificateSchema>;

// Content Processing Request
export const ContentRequestSchema = z.object({
  content: z.string(),
  tenant: z.string(),
  context: z.string(),
  policy: z.string().optional(),
  labels: z.array(z.string()).optional()
});

export type ContentRequest = z.infer<typeof ContentRequestSchema>;

// Content Processing Result
export const ContentResultSchema = z.object({
  content: z.string(),
  certificate: EgressCertificateSchema,
  processing_time: z.number(),
  blocked: z.boolean(),
  reason: z.string().optional()
});

export type ContentResult = z.infer<typeof ContentResultSchema>;

// Pattern for sensitive data detection
export interface SensitivePattern {
  name: string;
  pattern: RegExp;
  category: 'pii' | 'secret' | 'other';
  confidence: number;
  replacement?: string;
}

// Aho-Corasick implementation for pattern matching
class AhoCorasick {
  private root: TrieNode;
  private patterns: SensitivePattern[];

  constructor(patterns: SensitivePattern[]) {
    this.patterns = patterns;
    this.root = new TrieNode();
    this.buildTrie();
    this.buildFailureLinks();
  }

  private buildTrie(): void {
    for (const pattern of this.patterns) {
      let current = this.root;
      for (const char of pattern.pattern.source) {
        if (!current.children.has(char)) {
          current.children.set(char, new TrieNode());
        }
        current = current.children.get(char)!;
      }
      current.patterns.push(pattern);
    }
  }

  private buildFailureLinks(): void {
    const queue: TrieNode[] = [];
    
    // Initialize failure links for depth 1
    for (const [char, child] of this.root.children) {
      child.failure = this.root;
      queue.push(child);
    }

    // Build failure links for deeper levels
    while (queue.length > 0) {
      const current = queue.shift()!;
      
      for (const [char, child] of current.children) {
        let failure = current.failure;
        
        while (failure && !failure.children.has(char)) {
          failure = failure.failure;
        }
        
        child.failure = failure ? failure.children.get(char) || this.root : this.root;
        queue.push(child);
      }
    }
  }

  search(text: string): Array<{ pattern: SensitivePattern; start: number; end: number }> {
    const matches: Array<{ pattern: SensitivePattern; start: number; end: number }> = [];
    let current = this.root;

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      
      // Follow failure links until we find a match
      while (current && !current.children.has(char)) {
        current = current.failure!;
      }
      
      if (!current) {
        current = this.root;
        continue;
      }

      current = current.children.get(char)!;
      
      // Check for patterns at current node
      for (const pattern of current.patterns) {
        const start = i - pattern.pattern.source.length + 1;
        matches.push({ pattern, start, end: i + 1 });
      }

      // Follow failure links to find additional matches
      let failure = current.failure;
      while (failure) {
        for (const pattern of failure.patterns) {
          const start = i - pattern.pattern.source.length + 1;
          matches.push({ pattern, start, end: i + 1 });
        }
        failure = failure.failure;
      }
    }

    return matches;
  }
}

class TrieNode {
  children: Map<string, TrieNode> = new Map();
  patterns: SensitivePattern[] = [];
  failure: TrieNode | null = null;
}

// SimHash implementation for near-duplicate detection
class SimHash {
  private readonly hashBits = 64;

  compute(text: string): string {
    const hash = createHash('sha256').update(text).digest();
    const bits = new Array(this.hashBits).fill(0);

    // Convert hash to bit array
    for (let i = 0; i < hash.length && i * 8 < this.hashBits; i++) {
      const byte = hash[i];
      for (let j = 0; j < 8 && i * 8 + j < this.hashBits; j++) {
        bits[i * 8 + j] = (byte >> j) & 1;
      }
    }

    // Convert bits to hex string
    let result = '';
    for (let i = 0; i < this.hashBits; i += 4) {
      let nibble = 0;
      for (let j = 0; j < 4 && i + j < this.hashBits; j++) {
        nibble |= bits[i + j] << j;
      }
      result += nibble.toString(16);
    }

    return result;
  }

  similarity(hash1: string, hash2: string): number {
    if (hash1.length !== hash2.length) return 0;
    
    let differences = 0;
    for (let i = 0; i < hash1.length; i++) {
      if (hash1[i] !== hash2[i]) differences++;
    }
    
    return 1 - (differences / hash1.length);
  }
}

// MinHash implementation for similarity analysis
class MinHash {
  private readonly numHashes: number;
  private readonly hashFunctions: Array<(value: string) => number>;

  constructor(numHashes: number = 100) {
    this.numHashes = numHashes;
    this.hashFunctions = this.generateHashFunctions();
  }

  private generateHashFunctions(): Array<(value: string) => number> {
    const functions: Array<(value: string) => number> = [];
    
    for (let i = 0; i < this.numHashes; i++) {
      const a = Math.floor(Math.random() * 1000000) + 1;
      const b = Math.floor(Math.random() * 1000000) + 1;
      const p = 1000000007; // Large prime
      
      functions.push((value: string) => {
        const hash = createHash('sha256').update(value + i.toString()).digest('hex');
        const numericHash = parseInt(hash.substring(0, 8), 16);
        return (a * numericHash + b) % p;
      });
    }
    
    return functions;
  }

  compute(text: string): number[] {
    const words = text.toLowerCase().split(/\s+/);
    const signatures: number[] = [];
    
    for (const hashFn of this.hashFunctions) {
      let minHash = Infinity;
      for (const word of words) {
        const hash = hashFn(word);
        if (hash < minHash) minHash = hash;
      }
      signatures.push(minHash);
    }
    
    return signatures;
  }

  similarity(sig1: number[], sig2: number[]): number {
    if (sig1.length !== sig2.length) return 0;
    
    let matches = 0;
    for (let i = 0; i < sig1.length; i++) {
      if (sig1[i] === sig2[i]) matches++;
    }
    
    return matches / sig1.length;
  }
}

// Format and entropy analysis
class FormatAnalyzer {
  analyze(text: string): {
    entropy: number;
    hasStructuredData: boolean;
    dataTypes: string[];
    suspiciousPatterns: string[];
  } {
    const entropy = this.calculateEntropy(text);
    const hasStructuredData = this.detectStructuredData(text);
    const dataTypes = this.identifyDataTypes(text);
    const suspiciousPatterns = this.findSuspiciousPatterns(text);

    return {
      entropy,
      hasStructuredData,
      dataTypes,
      suspiciousPatterns
    };
  }

  private calculateEntropy(text: string): number {
    const charCount = new Map<string, number>();
    for (const char of text) {
      charCount.set(char, (charCount.get(char) || 0) + 1);
    }

    let entropy = 0;
    const length = text.length;
    
    for (const count of charCount.values()) {
      const probability = count / length;
      entropy -= probability * Math.log2(probability);
    }

    return entropy;
  }

  private detectStructuredData(text: string): boolean {
    const patterns = [
      /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/, // Credit card
      /\b\d{3}-\d{2}-\d{4}\b/, // SSN
      /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email
      /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/, // IP address
      /\b[A-Za-z0-9+/]{20,}={0,2}\b/, // Base64
      /\b[A-Fa-f0-9]{32,}\b/ // Hex strings
    ];

    return patterns.some(pattern => pattern.test(text));
  }

  private identifyDataTypes(text: string): string[] {
    const types: string[] = [];
    
    if (/\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/.test(text)) types.push('credit_card');
    if (/\b\d{3}-\d{2}-\d{4}\b/.test(text)) types.push('ssn');
    if (/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/.test(text)) types.push('email');
    if (/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/.test(text)) types.push('ip_address');
    if (/\b[A-Za-z0-9+/]{20,}={0,2}\b/.test(text)) types.push('base64');
    if (/\b[A-Fa-f0-9]{32,}\b/.test(text)) types.push('hex_string');
    if (/\b(api_key|password|secret|token)\s*[:=]\s*\S+/i.test(text)) types.push('credential');
    
    return types;
  }

  private findSuspiciousPatterns(text: string): string[] {
    const patterns: string[] = [];
    
    if (text.includes('DROP TABLE') || text.includes('INSERT INTO')) patterns.push('sql_injection');
    if (text.includes('<script>') || text.includes('javascript:')) patterns.push('xss');
    if (text.includes('rm -rf') || text.includes('cat /etc')) patterns.push('command_injection');
    if (text.includes('../../../')) patterns.push('path_traversal');
    if (text.includes('{{') || text.includes('${')) patterns.push('template_injection');
    
    return patterns;
  }
}

// LLM Analysis for ambiguous cases
class LLMAnalyzer {
  private readonly provider: string;
  private readonly apiKey?: string;

  constructor(provider: string = 'mock', apiKey?: string) {
    this.provider = provider;
    this.apiKey = apiKey;
  }

  async analyze(content: string, context: string): Promise<{
    isSensitive: boolean;
    confidence: number;
    reasoning: string;
    category: string;
  }> {
    // Mock implementation - in production this would call actual LLM APIs
    if (this.provider === 'mock') {
      return this.mockAnalysis(content, context);
    }

    // Real LLM implementation would go here
    throw new Error('Real LLM provider not implemented');
  }

  private mockAnalysis(content: string, context: string): {
    isSensitive: boolean;
    confidence: number;
    reasoning: string;
    category: string;
  } {
    const lowerContent = content.toLowerCase();
    
    // Simple heuristics for demonstration
    if (lowerContent.includes('password') || lowerContent.includes('secret')) {
      return {
        isSensitive: true,
        confidence: 0.9,
        reasoning: 'Contains credential-related terms',
        category: 'credential'
      };
    }

    if (lowerContent.includes('ssn') || lowerContent.includes('social security')) {
      return {
        isSensitive: true,
        confidence: 0.95,
        reasoning: 'Contains SSN-related terms',
        category: 'pii'
      };
    }

    if (lowerContent.includes('credit card') || lowerContent.includes('cc number')) {
      return {
        isSensitive: true,
        confidence: 0.9,
        reasoning: 'Contains credit card information',
        category: 'pii'
      };
    }

    return {
      isSensitive: false,
      confidence: 0.8,
      reasoning: 'No obvious sensitive content detected',
      category: 'safe'
    };
  }
}

// Main Egress Firewall class
export class EgressFirewall {
  private readonly patterns: SensitivePattern[];
  private readonly policies: string[];
  private readonly ahoCorasick: AhoCorasick;
  private readonly simHash: SimHash;
  private readonly minHash: MinHash;
  private readonly formatAnalyzer: FormatAnalyzer;
  private readonly llmAnalyzer: LLMAnalyzer;
  private readonly privateKey: Uint8Array;
  private readonly publicKey: Uint8Array;
  private readonly knownContentHashes: Set<string> = new Set();

  constructor(config: {
    patterns?: SensitivePattern[];
    policies: string[];
    llmProvider?: string;
    llmApiKey?: string;
    privateKeyHex: string;
  }) {
    this.patterns = config.patterns || this.getDefaultPatterns();
    this.policies = config.policies;
    this.ahoCorasick = new AhoCorasick(this.patterns);
    this.simHash = new SimHash();
    this.minHash = new MinHash();
    this.formatAnalyzer = new FormatAnalyzer();
    this.llmAnalyzer = new LLMAnalyzer(config.llmProvider || 'mock', config.llmApiKey);
    
    this.privateKey = Buffer.from(config.privateKeyHex, 'hex');
    this.publicKey = ed25519.getPublicKey(this.privateKey);
  }

  private getDefaultPatterns(): SensitivePattern[] {
    return [
      {
        name: 'credit_card',
        pattern: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/,
        category: 'pii',
        confidence: 0.95,
        replacement: '[CREDIT_CARD_MASKED]'
      },
      {
        name: 'ssn',
        pattern: /\b\d{3}-\d{2}-\d{4}\b/,
        category: 'pii',
        confidence: 0.95,
        replacement: '[SSN_MASKED]'
      },
      {
        name: 'email',
        pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
        category: 'pii',
        confidence: 0.9,
        replacement: '[EMAIL_MASKED]'
      },
      {
        name: 'api_key',
        pattern: /\b(api_key|api_key_id|access_key)\s*[:=]\s*[A-Za-z0-9+/]{20,}\b/i,
        category: 'secret',
        confidence: 0.9,
        replacement: '[API_KEY_MASKED]'
      },
      {
        name: 'password',
        pattern: /\b(password|passwd|pwd)\s*[:=]\s*\S+\b/i,
        category: 'secret',
        confidence: 0.9,
        replacement: '[PASSWORD_MASKED]'
      }
    ];
  }

  async process(request: ContentRequest): Promise<ContentResult> {
    const startTime = Date.now();
    
    try {
      // Validate request
      const validatedRequest = ContentRequestSchema.parse(request);
      
      // Stage 1: Aho-Corasick pattern matching
      const patternMatches = this.ahoCorasick.search(validatedRequest.content);
      
      // Stage 2: Format and entropy analysis
      const formatAnalysis = this.formatAnalyzer.analyze(validatedRequest.content);
      
      // Stage 3: SimHash for near-duplicate detection
      const contentHash = this.simHash.compute(validatedRequest.content);
      const isNearDupe = this.detectNearDuplicates(contentHash);
      
      // Stage 4: MinHash for similarity analysis (optional)
      const minHashSignature = this.minHash.compute(validatedRequest.content);
      
      // Stage 5: LLM analysis for ambiguous cases
      const llmAnalysis = await this.llmAnalyzer.analyze(
        validatedRequest.content, 
        validatedRequest.context
      );
      
      // Determine if content should be blocked
      const shouldBlock = this.shouldBlockContent(
        patternMatches,
        formatAnalysis,
        llmAnalysis,
        isNearDupe
      );
      
      // Generate certificate
      const certificate = await this.generateCertificate({
        patternMatches,
        formatAnalysis,
        llmAnalysis,
        isNearDupe,
        contentHash,
        shouldBlock,
        request: validatedRequest
      });
      
      // Process content (mask sensitive data if needed)
      const processedContent = this.processContent(
        validatedRequest.content,
        patternMatches
      );
      
      const processingTime = Date.now() - startTime;
      
      return {
        content: processedContent,
        certificate,
        processing_time: processingTime,
        blocked: shouldBlock,
        reason: shouldBlock ? 'Content blocked by egress firewall' : undefined
      };
      
    } catch (error) {
      const processingTime = Date.now() - startTime;
      
      // Generate error certificate
      const errorCertificate = await this.generateErrorCertificate(
        error instanceof Error ? error.message : 'Unknown error',
        request
      );
      
      return {
        content: request.content,
        certificate: errorCertificate,
        processing_time: processingTime,
        blocked: true,
        reason: 'Processing error'
      };
    }
  }

  private detectNearDuplicates(contentHash: string): boolean {
    // Check against known content hashes
    for (const knownHash of this.knownContentHashes) {
      if (this.simHash.similarity(contentHash, knownHash) > 0.8) {
        return true;
      }
    }
    
    // Add current hash to known hashes
    this.knownContentHashes.add(contentHash);
    return false;
  }

  private shouldBlockContent(
    patternMatches: Array<{ pattern: SensitivePattern; start: number; end: number }>,
    formatAnalysis: ReturnType<FormatAnalyzer['analyze']>,
    llmAnalysis: Awaited<ReturnType<LLMAnalyzer['analyze']>>,
    isNearDupe: boolean
  ): boolean {
    // Block if critical PII or secrets detected
    const hasCriticalPII = patternMatches.some(match => 
      match.pattern.category === 'pii' && match.pattern.confidence > 0.9
    );
    
    const hasSecrets = patternMatches.some(match => 
      match.pattern.category === 'secret' && match.pattern.confidence > 0.9
    );
    
    // Block if LLM analysis indicates sensitive content
    const llmSensitive = llmAnalysis.isSensitive && llmAnalysis.confidence > 0.8;
    
    // Block if suspicious patterns detected
    const hasSuspiciousPatterns = formatAnalysis.suspiciousPatterns.length > 0;
    
    return hasCriticalPII || hasSecrets || llmSensitive || hasSuspiciousPatterns;
  }

  private processContent(content: string, matches: Array<{ pattern: SensitivePattern; start: number; end: number }>): string {
    let processedContent = content;
    
    // Sort matches by start position in reverse order to avoid index shifting
    const sortedMatches = [...matches].sort((a, b) => b.start - a.start);
    
    for (const match of sortedMatches) {
      if (match.pattern.replacement) {
        processedContent = 
          processedContent.substring(0, match.start) +
          match.pattern.replacement +
          processedContent.substring(match.end);
      }
    }
    
    return processedContent;
  }

  private async generateCertificate(data: {
    patternMatches: Array<{ pattern: SensitivePattern; start: number; end: number }>;
    formatAnalysis: ReturnType<FormatAnalyzer['analyze']>;
    llmAnalysis: Awaited<ReturnType<LLMAnalyzer['analyze']>>;
    isNearDupe: boolean;
    contentHash: string;
    shouldBlock: boolean;
    request: ContentRequest;
  }): Promise<EgressCertificate> {
    const { patternMatches, formatAnalysis, llmAnalysis, isNearDupe, contentHash, shouldBlock, request } = data;
    
    // Determine PII status
    let pii: 'detected' | 'none' | 'masked' = 'none';
    if (patternMatches.some(m => m.pattern.category === 'pii')) {
      pii = shouldBlock ? 'masked' : 'detected';
    }
    
    // Determine secrets status
    let secrets: 'detected' | 'none' | 'masked' = 'none';
    if (patternMatches.some(m => m.pattern.category === 'secret')) {
      secrets = shouldBlock ? 'masked' : 'detected';
    }
    
    // Determine near-duplicate status
    const near_dupe: 'detected' | 'none' = isNearDupe ? 'detected' : 'none';
    
    // Determine non-interference status
    const non_interference: 'passed' | 'failed' = shouldBlock ? 'failed' : 'passed';
    
    // Generate policy hash
    const policyHash = createHash('sha256')
      .update(JSON.stringify(this.policies))
      .digest('hex');
    
    // Generate text hash
    const textHash = createHash('sha256')
      .update(request.content)
      .digest('hex');
    
    // Generate attestation reference
    const attestationRef = `attestation:${request.tenant}:${Date.now()}:${Math.random().toString(36).substring(7)}`;
    
    // Create certificate data
    const certificateData = {
      pii,
      secrets,
      near_dupe,
      non_interference,
      influencing_labels: request.labels || [],
      policy_hash: policyHash,
      text_hash: textHash,
      attestation_ref: attestationRef
    };
    
    // Sign the certificate
    const dataString = JSON.stringify(certificateData, Object.keys(certificateData).sort());
    const message = Buffer.from(dataString, 'utf8');
    const signature = await ed25519.sign(message, this.privateKey);
    const sig = Buffer.from(signature).toString('hex');
    
    return {
      ...certificateData,
      sig
    };
  }

  private async generateErrorCertificate(error: string, request: ContentRequest): Promise<EgressCertificate> {
    const policyHash = createHash('sha256')
      .update(JSON.stringify(this.policies))
      .digest('hex');
    
    const textHash = createHash('sha256')
      .update(request.content)
      .digest('hex');
    
    const attestationRef = `error:${request.tenant}:${Date.now()}`;
    
    const certificateData = {
      pii: 'none' as const,
      secrets: 'none' as const,
      near_dupe: 'none' as const,
      non_interference: 'failed' as const,
      influencing_labels: request.labels || [],
      policy_hash: policyHash,
      text_hash: textHash,
      attestation_ref: attestationRef
    };
    
    const dataString = JSON.stringify(certificateData, Object.keys(certificateData).sort());
    const message = Buffer.from(dataString, 'utf8');
    const signature = await ed25519.sign(message, this.privateKey);
    const sig = Buffer.from(signature).toString('hex');
    
    return {
      ...certificateData,
      sig
    };
  }

  // Verify certificate signature
  async verifyCertificate(certificate: EgressCertificate): Promise<boolean> {
    try {
      const { sig, ...dataToSign } = certificate;
      const dataString = JSON.stringify(dataToSign, Object.keys(dataToSign).sort());
      const message = Buffer.from(dataString, 'utf8');
      
      const signature = Buffer.from(sig, 'hex');
      const isValid = await ed25519.verify(signature, message, this.publicKey);
      
      return isValid;
    } catch (error) {
      return false;
    }
  }

  // Get public key for verification
  getPublicKey(): string {
    return Buffer.from(this.publicKey).toString('hex');
  }

  // Get processing statistics
  getStats(): {
    totalProcessed: number;
    blockedCount: number;
    piiDetected: number;
    secretsDetected: number;
    nearDuplicatesDetected: number;
    averageProcessingTime: number;
  } {
    // This would track actual statistics in production
    return {
      totalProcessed: 0,
      blockedCount: 0,
      piiDetected: 0,
      secretsDetected: 0,
      nearDuplicatesDetected: 0,
      averageProcessingTime: 0
    };
  }
}

// Export factory function
export const createEgressFirewall = (config: {
  patterns?: SensitivePattern[];
  policies: string[];
  llmProvider?: string;
  llmApiKey?: string;
  privateKeyHex: string;
}): EgressFirewall => {
  return new EgressFirewall(config);
};
