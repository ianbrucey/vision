# Authentication & Authorization Context

## Current Architecture
**Authentication Method**: [e.g., JWT tokens, sessions, OAuth, SAML]

**Token Storage**: [Where tokens are stored - localStorage, cookies, secure storage]

**Session Management**: [How sessions are handled - server-side, client-side, hybrid]

**Authorization Pattern**: [Role-based, permission-based, attribute-based, etc.]

**Identity Provider**: [Internal, Auth0, Firebase, AWS Cognito, etc.]

## Key Components
**Authentication Service**: [Location and purpose]
- File: `[path/to/auth/service]`
- Responsibilities: [Token generation, validation, refresh]
- Dependencies: [External services, databases, libraries]

**Middleware**: [Authentication middleware]
- File: `[path/to/auth/middleware]`
- Usage: [How to apply to routes/endpoints]
- Configuration: [Required settings and environment variables]

**User Model**: [User data structure]
- File: `[path/to/user/model]`
- Key fields: [id, email, roles, permissions, etc.]
- Relationships: [Connected entities and their purposes]

**Token Utilities**: [JWT or token handling]
- File: `[path/to/token/utils]`
- Functions: [generate, validate, refresh, revoke]
- Configuration: [Secrets, expiration times, algorithms]

## Security Patterns to Follow
**Route Protection**:
```javascript
// Example pattern for protecting routes
router.get('/protected', authMiddleware, (req, res) => {
  // Protected route logic
});
```

**Token Validation**:
- Always validate tokens server-side
- Check token expiration and signature
- Verify token issuer and audience
- Handle refresh tokens securely
- Implement token blacklisting for logout

**Password Handling**:
- Use strong hashing algorithms (bcrypt, Argon2)
- Implement proper salt generation
- Enforce password complexity requirements
- Implement rate limiting for login attempts

**Error Handling**:
- Return 401 for authentication failures
- Return 403 for authorization failures
- Provide clear but secure error messages
- Log security events for monitoring
- Never expose sensitive information in errors

## Security Requirements
**Password Security**:
- Hashing algorithm: [bcrypt, Argon2, etc.]
- Salt rounds/iterations: [Specific configuration]
- Password complexity: [Minimum requirements]
- Password history: [Prevent reuse policy]

**Token Security**:
- Access token expiration: [Time limit]
- Refresh token expiration: [Time limit]
- Token rotation strategy: [When and how tokens are refreshed]
- Token revocation: [How to invalidate tokens]
- Secure transmission: [HTTPS, secure headers]

**Session Security**:
- Session timeout: [Idle and absolute timeouts]
- Session storage: [Where and how sessions are stored]
- Session invalidation: [Logout and security events]
- Concurrent sessions: [Policy for multiple sessions]

**API Security**:
- Rate limiting: [Requests per time period]
- CORS configuration: [Allowed origins and methods]
- Input validation: [Authentication parameter validation]
- CSRF protection: [Token-based or SameSite cookies]

## Integration Points
**Frontend Integration**:
- Login endpoint: `[POST /api/auth/login]`
- Logout endpoint: `[POST /api/auth/logout]`
- Token refresh: `[POST /api/auth/refresh]`
- User profile: `[GET /api/user/profile]`
- Password reset: `[POST /api/auth/reset-password]`

**Database Integration**:
- Users table/collection: `[table/collection name and schema]`
- Sessions table: `[if using session storage]`
- Roles/permissions: `[authorization data structure]`
- Audit logs: `[security event logging]`

**External Services**:
- Identity providers: `[OAuth providers, SAML, etc.]`
- Email service: `[For password reset, verification]`
- SMS service: `[For 2FA, if applicable]`
- Monitoring: `[Security event monitoring]`

## Testing Requirements
**Unit Tests**:
- [ ] Authentication service functions
- [ ] Token generation and validation
- [ ] Password hashing and verification
- [ ] Middleware functionality
- [ ] Authorization logic

**Integration Tests**:
- [ ] Login flow end-to-end
- [ ] Protected route access
- [ ] Token refresh mechanism
- [ ] Logout and session cleanup
- [ ] Password reset flow

**Security Tests**:
- [ ] Invalid token handling
- [ ] Expired token behavior
- [ ] Brute force protection
- [ ] SQL injection prevention
- [ ] XSS protection in auth forms
- [ ] CSRF protection validation

**Performance Tests**:
- [ ] Authentication endpoint load testing
- [ ] Token validation performance
- [ ] Database query optimization
- [ ] Concurrent user handling

## Common Implementation Patterns
**User Registration**:
```javascript
// Example registration pattern
const hashedPassword = await bcrypt.hash(password, 12);
const user = await User.create({
  email: email.toLowerCase(),
  password: hashedPassword,
  role: 'user',
  emailVerified: false
});
```

**Login Verification**:
```javascript
// Example login pattern
const user = await User.findByEmail(email.toLowerCase());
if (!user || !user.emailVerified) {
  throw new AuthenticationError('Invalid credentials');
}
const isValid = await bcrypt.compare(password, user.password);
if (isValid) {
  const token = jwt.sign(
    { userId: user.id, role: user.role }, 
    process.env.JWT_SECRET,
    { expiresIn: '15m' }
  );
  return { token, user: user.publicProfile() };
}
```

**Authorization Middleware**:
```javascript
// Example authorization pattern
const requireRole = (role) => (req, res, next) => {
  if (!req.user || !req.user.roles.includes(role)) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }
  next();
};
```

## Troubleshooting Guide
**Common Issues**:
- Token expiration handling
- CORS issues with auth headers
- Session persistence problems
- Role/permission edge cases
- Password reset token validation

**Debug Steps**:
1. Check token validity and expiration
2. Verify middleware is applied correctly
3. Confirm user permissions in database
4. Review authentication logs
5. Test with different user roles
6. Validate environment configuration

**Monitoring & Alerts**:
- Failed login attempts (potential brute force)
- Unusual authentication patterns
- Token validation failures
- Permission escalation attempts
- Account lockouts and unlocks

## Compliance Considerations
**Data Protection**:
- GDPR compliance for user data
- Data retention policies
- Right to be forgotten implementation
- Data encryption requirements

**Security Standards**:
- OWASP authentication guidelines
- Industry-specific compliance (HIPAA, PCI-DSS)
- Security audit requirements
- Penetration testing recommendations

---

**Last Updated**: [Date]
**Maintained By**: [Team/Person responsible]
**Review Schedule**: [How often this should be reviewed]
