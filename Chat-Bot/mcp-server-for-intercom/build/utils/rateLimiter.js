export class RateLimiter {
    tokens;
    lastRefill;
    maxTokens;
    refillInterval;
    tokenRate; // Tokens added per millisecond
    constructor(maxTokens, refillInterval) {
        this.maxTokens = maxTokens;
        this.tokens = maxTokens;
        this.lastRefill = Date.now();
        this.refillInterval = refillInterval;
        // Calculate token rate per millisecond for gradual refill
        this.tokenRate = maxTokens / refillInterval;
    }
    tryAcquire() {
        this.refill();
        if (this.tokens >= 1) {
            this.tokens -= 1;
            return true;
        }
        return false;
    }
    refill() {
        const now = Date.now();
        const elapsedMs = now - this.lastRefill;
        if (elapsedMs > 0) {
            // Add tokens based on elapsed time
            const newTokens = elapsedMs * this.tokenRate;
            // Update token count, but don't exceed max
            this.tokens = Math.min(this.tokens + newTokens, this.maxTokens);
            // Update last refill time
            this.lastRefill = now;
        }
    }
}
