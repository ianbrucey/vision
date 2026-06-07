# API Design & Implementation Context

## API Architecture
**API Style**: [REST, GraphQL, gRPC, etc.]

**Base URL Structure**: [https://api.example.com/v1/]

**Versioning Strategy**: [URL versioning, header versioning, etc.]

**Documentation**: [OpenAPI/Swagger, GraphQL schema, etc.]

## RESTful Design Patterns
**Resource Naming**:
- Use nouns for resources: `/users`, `/posts`, `/comments`
- Use plural nouns: `/users` not `/user`
- Nested resources: `/users/{id}/posts`
- Avoid deep nesting (max 2 levels)

**HTTP Methods**:
- GET: Retrieve resources (idempotent)
- POST: Create new resources
- PUT: Update entire resource (idempotent)
- PATCH: Partial resource updates
- DELETE: Remove resources (idempotent)

**Status Codes**:
```javascript
// Standard status code usage
200 OK          // Successful GET, PUT, PATCH
201 Created     // Successful POST
204 No Content  // Successful DELETE
400 Bad Request // Client error
401 Unauthorized // Authentication required
403 Forbidden   // Authorization failed
404 Not Found   // Resource doesn't exist
409 Conflict    // Resource conflict
422 Unprocessable Entity // Validation errors
500 Internal Server Error // Server error
```

## Request/Response Patterns
**Request Structure**:
```javascript
// Example request patterns
// GET with query parameters
GET /api/v1/users?page=1&limit=20&sort=created_at&order=desc

// POST with JSON body
POST /api/v1/users
Content-Type: application/json
{
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user"
}

// PATCH with partial updates
PATCH /api/v1/users/123
Content-Type: application/json
{
  "name": "Jane Doe"
}
```

**Response Structure**:
```javascript
// Success response format
{
  "success": true,
  "data": {
    "id": "123",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2023-01-01T00:00:00Z"
  },
  "meta": {
    "timestamp": "2023-01-01T00:00:00Z",
    "version": "1.0"
  }
}

// Error response format
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Email is required"
      }
    ]
  },
  "meta": {
    "timestamp": "2023-01-01T00:00:00Z",
    "request_id": "req_123456"
  }
}
```

## Authentication & Authorization
**Authentication Methods**:
- Bearer tokens (JWT)
- API keys
- OAuth 2.0
- Basic authentication (development only)

**Authorization Patterns**:
```javascript
// Route protection middleware
const requireAuth = (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  // Validate token and set req.user
  next();
};

// Role-based authorization
const requireRole = (role) => (req, res, next) => {
  if (!req.user.roles.includes(role)) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }
  next();
};
```

## Input Validation & Sanitization
**Validation Patterns**:
```javascript
// Example validation middleware
const validateUser = (req, res, next) => {
  const schema = Joi.object({
    email: Joi.string().email().required(),
    name: Joi.string().min(2).max(100).required(),
    age: Joi.number().integer().min(0).max(150).optional()
  });
  
  const { error, value } = schema.validate(req.body);
  if (error) {
    return res.status(422).json({
      error: 'Validation failed',
      details: error.details.map(d => ({
        field: d.path.join('.'),
        message: d.message
      }))
    });
  }
  
  req.validatedData = value;
  next();
};
```

**Sanitization Guidelines**:
- Trim whitespace from string inputs
- Convert email addresses to lowercase
- Escape HTML content to prevent XSS
- Validate and sanitize file uploads
- Implement rate limiting per endpoint

## Error Handling
**Error Categories**:
```javascript
// Standardized error types
class APIError extends Error {
  constructor(message, statusCode, code) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
  }
}

class ValidationError extends APIError {
  constructor(details) {
    super('Validation failed', 422, 'VALIDATION_ERROR');
    this.details = details;
  }
}

class NotFoundError extends APIError {
  constructor(resource) {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}
```

**Global Error Handler**:
```javascript
// Express error handling middleware
const errorHandler = (err, req, res, next) => {
  const statusCode = err.statusCode || 500;
  const response = {
    success: false,
    error: {
      code: err.code || 'INTERNAL_ERROR',
      message: err.message || 'Internal server error'
    },
    meta: {
      timestamp: new Date().toISOString(),
      request_id: req.id
    }
  };
  
  if (err.details) {
    response.error.details = err.details;
  }
  
  // Log error for monitoring
  console.error(`API Error: ${err.message}`, {
    statusCode,
    code: err.code,
    stack: err.stack,
    requestId: req.id
  });
  
  res.status(statusCode).json(response);
};
```

## Pagination & Filtering
**Pagination Patterns**:
```javascript
// Offset-based pagination
GET /api/v1/users?page=1&limit=20

// Cursor-based pagination (for large datasets)
GET /api/v1/users?cursor=eyJpZCI6MTIzfQ&limit=20

// Response with pagination metadata
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

**Filtering & Sorting**:
```javascript
// Query parameter patterns
GET /api/v1/users?
  filter[status]=active&
  filter[role]=admin&
  sort=created_at&
  order=desc&
  search=john

// Implementation example
const buildQuery = (req) => {
  const { filter = {}, sort, order = 'asc', search } = req.query;
  
  let query = {};
  
  // Apply filters
  Object.keys(filter).forEach(key => {
    if (allowedFilters.includes(key)) {
      query[key] = filter[key];
    }
  });
  
  // Apply search
  if (search) {
    query.$or = [
      { name: { $regex: search, $options: 'i' } },
      { email: { $regex: search, $options: 'i' } }
    ];
  }
  
  return query;
};
```

## Performance Optimization
**Caching Strategies**:
```javascript
// Response caching middleware
const cache = (duration = 300) => (req, res, next) => {
  const key = `cache:${req.originalUrl}`;
  
  redis.get(key, (err, cached) => {
    if (cached) {
      return res.json(JSON.parse(cached));
    }
    
    // Override res.json to cache response
    const originalJson = res.json;
    res.json = function(data) {
      redis.setex(key, duration, JSON.stringify(data));
      return originalJson.call(this, data);
    };
    
    next();
  });
};
```

**Database Query Optimization**:
- Use database indexes for filtered fields
- Implement eager loading for related data
- Use database-level pagination
- Avoid N+1 query problems
- Implement query result caching

## Rate Limiting & Security
**Rate Limiting**:
```javascript
// Rate limiting configuration
const rateLimit = require('express-rate-limit');

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false
});

// Different limits for different endpoints
const strictLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5, // stricter limit for sensitive endpoints
  skipSuccessfulRequests: true
});
```

**Security Headers**:
```javascript
// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"]
    }
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// CORS configuration
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

## Testing Strategies
**Unit Tests**:
```javascript
// Example API endpoint test
describe('POST /api/v1/users', () => {
  it('should create a new user with valid data', async () => {
    const userData = {
      email: 'test@example.com',
      name: 'Test User'
    };
    
    const response = await request(app)
      .post('/api/v1/users')
      .send(userData)
      .expect(201);
    
    expect(response.body.success).toBe(true);
    expect(response.body.data.email).toBe(userData.email);
  });
  
  it('should return validation error for invalid email', async () => {
    const userData = {
      email: 'invalid-email',
      name: 'Test User'
    };
    
    const response = await request(app)
      .post('/api/v1/users')
      .send(userData)
      .expect(422);
    
    expect(response.body.success).toBe(false);
    expect(response.body.error.code).toBe('VALIDATION_ERROR');
  });
});
```

**Integration Tests**:
- Test complete request/response cycles
- Test authentication and authorization
- Test error handling scenarios
- Test rate limiting behavior
- Test database interactions

## Documentation Standards
**OpenAPI/Swagger**:
```yaml
# Example OpenAPI specification
paths:
  /users:
    post:
      summary: Create a new user
      tags:
        - Users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserRequest'
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '422':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

## Monitoring & Logging
**Request Logging**:
```javascript
// Request logging middleware
const requestLogger = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log({
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration,
      userAgent: req.get('User-Agent'),
      ip: req.ip,
      requestId: req.id
    });
  });
  
  next();
};
```

**Health Checks**:
```javascript
// Health check endpoint
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      database: await checkDatabaseHealth(),
      redis: await checkRedisHealth(),
      external_api: await checkExternalAPIHealth()
    }
  };
  
  const isHealthy = Object.values(health.services)
    .every(service => service.status === 'healthy');
  
  res.status(isHealthy ? 200 : 503).json(health);
});
```

---

**Last Updated**: [Date]
**Maintained By**: [Team/Person responsible]
**Review Schedule**: [How often this should be reviewed]
