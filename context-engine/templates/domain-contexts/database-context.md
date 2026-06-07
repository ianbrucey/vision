# Database Operations Context

## Database Architecture
**Database Type**: [PostgreSQL, MySQL, MongoDB, etc.]

**Connection Strategy**: [Connection pooling, single connection, etc.]

**Environment Configuration**:
- Development: [Database name, host, credentials management]
- Staging: [Database name, host, credentials management]
- Production: [Database name, host, credentials management]

**Backup Strategy**: [Automated backups, retention policy, recovery procedures]

## Schema Design Patterns
**Naming Conventions**:
- Tables: [snake_case, PascalCase, etc.]
- Columns: [snake_case, camelCase, etc.]
- Indexes: [Naming pattern for indexes]
- Foreign Keys: [Naming pattern for relationships]

**Data Types**:
- Primary Keys: [UUID, auto-increment, etc.]
- Timestamps: [UTC, timezone handling]
- Text Fields: [VARCHAR limits, TEXT usage]
- Numeric Fields: [Precision, scale considerations]

**Relationship Patterns**:
- One-to-Many: [Standard implementation approach]
- Many-to-Many: [Junction table patterns]
- Polymorphic: [How to handle polymorphic relationships]

## Migration Management
**Migration Tools**: [Sequelize, Knex, Alembic, etc.]

**Migration Patterns**:
```sql
-- Example migration structure
-- Up migration
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Down migration
DROP TABLE users;
```

**Migration Guidelines**:
- Always include both up and down migrations
- Test migrations on staging before production
- Include data migrations when schema changes affect existing data
- Use transactions for complex migrations
- Document breaking changes and rollback procedures

## Query Optimization
**Indexing Strategy**:
- Primary indexes: [Automatic on primary keys]
- Foreign key indexes: [Index all foreign keys]
- Query-specific indexes: [Based on common query patterns]
- Composite indexes: [Multi-column index strategy]

**Query Patterns**:
```sql
-- Efficient query patterns
-- Use indexes effectively
SELECT * FROM users WHERE email = $1; -- Indexed column

-- Avoid N+1 queries with joins
SELECT u.*, p.title 
FROM users u 
LEFT JOIN posts p ON u.id = p.user_id 
WHERE u.active = true;

-- Use LIMIT for pagination
SELECT * FROM posts 
ORDER BY created_at DESC 
LIMIT 20 OFFSET $1;
```

**Performance Guidelines**:
- Use EXPLAIN ANALYZE to understand query performance
- Avoid SELECT * in production queries
- Use appropriate JOIN types
- Implement proper pagination
- Monitor slow query logs

## Data Access Layer
**ORM/Query Builder**: [Sequelize, TypeORM, Prisma, etc.]

**Connection Management**:
```javascript
// Example connection configuration
const dbConfig = {
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  username: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  pool: {
    min: 2,
    max: 10,
    acquire: 30000,
    idle: 10000
  }
};
```

**Model Patterns**:
```javascript
// Example model definition
class User extends Model {
  static associate(models) {
    User.hasMany(models.Post, { foreignKey: 'userId' });
    User.belongsToMany(models.Role, { through: 'UserRoles' });
  }
  
  // Instance methods
  async getPosts() {
    return this.getPosts({ order: [['createdAt', 'DESC']] });
  }
  
  // Class methods
  static async findByEmail(email) {
    return this.findOne({ where: { email: email.toLowerCase() } });
  }
}
```

## Transaction Management
**Transaction Patterns**:
```javascript
// Example transaction usage
const transaction = await sequelize.transaction();
try {
  const user = await User.create(userData, { transaction });
  const profile = await Profile.create(profileData, { transaction });
  await transaction.commit();
  return { user, profile };
} catch (error) {
  await transaction.rollback();
  throw error;
}
```

**Transaction Guidelines**:
- Use transactions for multi-table operations
- Keep transactions as short as possible
- Handle rollbacks properly
- Avoid nested transactions unless supported
- Monitor transaction deadlocks

## Data Validation & Constraints
**Database-Level Constraints**:
- NOT NULL constraints for required fields
- UNIQUE constraints for unique fields
- CHECK constraints for data validation
- Foreign key constraints for referential integrity

**Application-Level Validation**:
```javascript
// Example validation patterns
const userSchema = {
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      isEmail: true,
      len: [1, 255]
    }
  },
  age: {
    type: DataTypes.INTEGER,
    validate: {
      min: 0,
      max: 150
    }
  }
};
```

## Security Considerations
**SQL Injection Prevention**:
- Always use parameterized queries
- Validate and sanitize input data
- Use ORM/query builder security features
- Implement input length limits

**Access Control**:
- Database user permissions
- Connection string security
- Environment variable management
- Network security (VPC, firewall rules)

**Data Encryption**:
- Encryption at rest
- Encryption in transit (SSL/TLS)
- Sensitive field encryption
- Key management practices

## Testing Strategies
**Unit Tests**:
- Model validation tests
- Query logic tests
- Transaction handling tests
- Error condition tests

**Integration Tests**:
- Database connection tests
- Migration tests
- Full CRUD operation tests
- Performance tests

**Test Database Management**:
```javascript
// Example test database setup
beforeEach(async () => {
  await sequelize.sync({ force: true });
  await seedTestData();
});

afterEach(async () => {
  await sequelize.drop();
});
```

## Monitoring & Maintenance
**Performance Monitoring**:
- Query execution time tracking
- Connection pool monitoring
- Database size and growth tracking
- Index usage analysis

**Health Checks**:
```javascript
// Example database health check
async function checkDatabaseHealth() {
  try {
    await sequelize.authenticate();
    return { status: 'healthy', timestamp: new Date() };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}
```

**Maintenance Tasks**:
- Regular backup verification
- Index maintenance and optimization
- Statistics updates
- Log rotation and cleanup

## Common Patterns
**Soft Deletes**:
```javascript
// Soft delete implementation
const User = sequelize.define('User', {
  // ... other fields
  deletedAt: {
    type: DataTypes.DATE,
    allowNull: true
  }
}, {
  paranoid: true // Enables soft deletes
});
```

**Audit Trails**:
```javascript
// Audit trail pattern
const AuditLog = sequelize.define('AuditLog', {
  tableName: DataTypes.STRING,
  recordId: DataTypes.STRING,
  action: DataTypes.ENUM('CREATE', 'UPDATE', 'DELETE'),
  oldValues: DataTypes.JSONB,
  newValues: DataTypes.JSONB,
  userId: DataTypes.UUID,
  timestamp: DataTypes.DATE
});
```

**Pagination**:
```javascript
// Pagination helper
async function paginateResults(model, page = 1, limit = 20, where = {}) {
  const offset = (page - 1) * limit;
  const { count, rows } = await model.findAndCountAll({
    where,
    limit,
    offset,
    order: [['createdAt', 'DESC']]
  });
  
  return {
    data: rows,
    pagination: {
      page,
      limit,
      total: count,
      pages: Math.ceil(count / limit)
    }
  };
}
```

## Troubleshooting
**Common Issues**:
- Connection pool exhaustion
- Query timeout errors
- Migration failures
- Constraint violations
- Performance degradation

**Debug Steps**:
1. Check database connectivity
2. Review query execution plans
3. Monitor connection pool status
4. Analyze slow query logs
5. Verify index usage
6. Check for blocking transactions

---

**Last Updated**: [Date]
**Maintained By**: [Team/Person responsible]
**Review Schedule**: [How often this should be reviewed]
