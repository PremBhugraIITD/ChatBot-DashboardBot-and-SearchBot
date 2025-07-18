export class TokenBucketRateLimiter {
    constructor(maxRequests, windowMs) {
        this.maxTokens = maxRequests;
        this.tokens = maxRequests;
        this.lastRefill = Date.now();
        this.refillInterval = windowMs;
        this.refillRate = maxRequests / windowMs;
    }
    refillTokens() {
        const now = Date.now();
        const timePassed = now - this.lastRefill;
        const newTokens = timePassed * this.refillRate;
        this.tokens = Math.min(this.maxTokens, this.tokens + newTokens);
        this.lastRefill = now;
    }
    canMakeRequest() {
        this.refillTokens();
        if (this.tokens >= 1) {
            this.tokens -= 1;
            return true;
        }
        return false;
    }
    async waitForAvailableToken() {
        return new Promise((resolve) => {
            const check = () => {
                if (this.canMakeRequest()) {
                    resolve();
                }
                else {
                    // Calculate time until next token is available
                    const tokensNeeded = 1 - this.tokens;
                    const msToWait = (tokensNeeded / this.refillRate) * 1000;
                    setTimeout(check, Math.min(msToWait, 100)); // Check at most every 100ms
                }
            };
            check();
        });
    }
}
// Create rate limiters based on Trello's limits
export const createTrelloRateLimiters = () => {
    const apiKeyLimiter = new TokenBucketRateLimiter(300, 10000); // 300 requests per 10 seconds
    const tokenLimiter = new TokenBucketRateLimiter(100, 10000); // 100 requests per 10 seconds
    return {
        apiKeyLimiter,
        tokenLimiter,
        /**
         * Checks if a request can be made without hitting rate limits.
         * This is useful for pre-checking before attempting a request,
         * allowing for more graceful handling of rate limits without blocking.
         *
         * @returns {boolean} True if both API key and token limiters have available tokens
         */
        canMakeRequest() {
            return apiKeyLimiter.canMakeRequest() && tokenLimiter.canMakeRequest();
        },
        /**
         * Waits until tokens are available for both API key and token limiters.
         * This method blocks execution until rate limits allow the request to proceed.
         * Used by the axios interceptor to ensure all requests respect Trello's rate limits.
         *
         * @returns {Promise<void>} Resolves when tokens are available
         */
        async waitForAvailableToken() {
            await Promise.all([
                apiKeyLimiter.waitForAvailableToken(),
                tokenLimiter.waitForAvailableToken(),
            ]);
        },
    };
};
//# sourceMappingURL=rate-limiter.js.map