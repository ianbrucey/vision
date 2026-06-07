# Coding Patterns

> **Purpose:** Backend patterns and architectural rules  
> **Rule:** All code must follow these patterns. No improvisation.

---

## How to Use This File

Each pattern entry should include:
- **Pattern Name**: Clear identifier
- **When to Use**: Specific scenarios
- **Implementation**: Code example
- **Anti-Pattern**: What NOT to do

---

## Example Entry

### Error Handling

**When to Use:** All external API calls, database operations, file I/O

**Implementation:**
```python
try:
    result = external_api.fetch_data()
    return {"success": True, "data": result}
except APIException as e:
    logger.error(f"API call failed: {e}")
    return {"success": False, "error": str(e)}
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    return {"success": False, "error": "Internal server error"}
```

**Anti-Pattern (DO NOT DO THIS):**
```python
# ❌ No error handling
result = external_api.fetch_data()
return result

# ❌ Bare except
try:
    result = external_api.fetch_data()
except:
    pass
```

**Rules:**
- Always catch specific exceptions first
- Log errors with context
- Return structured error responses
- Never use bare `except:` clauses

---

## Example Entry: Repository Pattern

**When to Use:** All database access

**Implementation:**
```python
class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create(self, user_data: dict) -> User:
        """Create new user."""
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        return user
```

**Anti-Pattern (DO NOT DO THIS):**
```python
# ❌ Direct database access in controllers
def get_user(user_id):
    return db.query(User).filter(User.id == user_id).first()
```

**Rules:**
- All database queries go through repositories
- Repositories return domain models, not raw SQL results
- Controllers never import database session directly

---

<!-- Add your patterns below -->

