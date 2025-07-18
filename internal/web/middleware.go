package web

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// CORSMiddleware adds CORS headers to responses
func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Credentials", "true")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Header("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

// LoggingMiddleware logs HTTP requests with structured logging
func LoggingMiddleware(logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		raw := c.Request.URL.RawQuery

		// Process request
		c.Next()

		// Calculate request duration
		duration := time.Since(start)

		// Build log entry
		entry := logger.WithFields(logrus.Fields{
			"method":     c.Request.Method,
			"path":       path,
			"status":     c.Writer.Status(),
			"duration":   duration,
			"client_ip":  c.ClientIP(),
			"user_agent": c.Request.UserAgent(),
		})

		if raw != "" {
			entry = entry.WithField("query", raw)
		}

		// Log based on status code
		switch {
		case c.Writer.Status() >= 500:
			entry.Error("Server error")
		case c.Writer.Status() >= 400:
			entry.Warn("Client error")
		default:
			entry.Info("Request completed")
		}
	}
}

// RateLimitMiddleware provides basic rate limiting
// TODO: Implement proper rate limiting with redis or in-memory store
func RateLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Placeholder for rate limiting implementation
		// This would typically use a rate limiter like:
		// - go.uber.org/ratelimit
		// - golang.org/x/time/rate
		// - redis-based rate limiting
		
		c.Next()
	}
}

// AuthMiddleware provides authentication for protected routes
// TODO: Implement proper authentication (JWT, session-based, etc.)
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Placeholder for authentication implementation
		// This would typically:
		// 1. Extract token from Authorization header or cookie
		// 2. Validate the token
		// 3. Set user context
		// 4. Allow or deny the request
		
		c.Next()
	}
}

// SecurityHeadersMiddleware adds security headers to responses
func SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Prevent XSS attacks
		c.Header("X-Content-Type-Options", "nosniff")
		c.Header("X-Frame-Options", "DENY")
		c.Header("X-XSS-Protection", "1; mode=block")
		
		// HSTS for HTTPS (only add if using HTTPS)
		// c.Header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		
		// Content Security Policy (basic policy)
		c.Header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'")
		
		c.Next()
	}
}

// RequestIDMiddleware adds a unique request ID to each request
func RequestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Check if request ID already exists (from load balancer, etc.)
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			// Generate a simple request ID (in production, use UUID)
			requestID = generateRequestID()
		}
		
		// Set request ID in context and response header
		c.Header("X-Request-ID", requestID)
		c.Set("request_id", requestID)
		
		c.Next()
	}
}

// generateRequestID generates a simple request ID
// TODO: Replace with proper UUID generation
func generateRequestID() string {
	return time.Now().Format("20060102150405") + "-" + "placeholder"
}

// RecoveryMiddleware provides custom panic recovery
func RecoveryMiddleware(logger *logrus.Logger) gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, recovered interface{}) {
		logger.WithFields(logrus.Fields{
			"panic":      recovered,
			"method":     c.Request.Method,
			"path":       c.Request.URL.Path,
			"client_ip":  c.ClientIP(),
			"user_agent": c.Request.UserAgent(),
		}).Error("Panic recovered")
		
		c.JSON(500, gin.H{
			"error":   "Internal server error",
			"message": "The server encountered an unexpected error",
		})
	})
}