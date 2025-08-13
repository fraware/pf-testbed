// Test setup file for Jest
import { TextEncoder, TextDecoder } from "util";

// Mock crypto for consistent testing
(global as any).TextEncoder = TextEncoder;
(global as any).TextDecoder = TextDecoder;

// Mock environment variables
process.env["NODE_ENV"] = "test";
process.env["PF_SIGNATURE_SECRET"] = "test-secret-key";

// Global test utilities
global.console = {
  ...console,
  // Suppress console.log during tests unless explicitly needed
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});

// Global test timeout
jest.setTimeout(10000);
