# [Domain Name] Context

> **Purpose:** Onboard developers (human or AI) to this domain
> **Last Updated:** [Date]
> **Maintained By:** [Person/Team]

---

## 1. Business Overview

### What This Domain Does
[2-3 sentences explaining the business purpose of this domain]

### Key Business Rules
- [ ] Rule 1: [e.g., "Events cannot be cancelled within 2 hours of start time"]
- [ ] Rule 2: [e.g., "Paid events require Stripe integration"]
- [ ] Rule 3: [e.g., "Refunds are automatic if cancelled 24+ hours before"]

### User Stories This Supports
- As a [user type], I can [action] so that [outcome]
- As a [user type], I can [action] so that [outcome]

---

## 2. Code Navigation Guide

> **Start here when working on this domain**

### Entry Points
| If you want to... | Start at... | Then follow... |
|-------------------|-------------|----------------|
| Understand the data model | `app/Models/[Model].php` | Relationships defined in model |
| See the API endpoints | `routes/api.php` | Search for `[resource]` |
| Trace a user action | `app/Http/Controllers/[Controller].php` | Method → Service → Repository |
| Modify database | `database/migrations/*[table]*` | Check existing columns first |

### Key Files (Read These First)
| File | Purpose | Key Methods/Properties |
|------|---------|------------------------|
| `app/Models/Event.php` | Event entity | `attendees()`, `payments()`, `canCancel()` |
| `app/Services/EventService.php` | Business logic | `createEvent()`, `cancelEvent()` |
| `app/Http/Controllers/EventController.php` | API layer | Standard CRUD + custom actions |

### File Relationships (How Data Flows)
```
Request → Controller → Service → Repository → Model → Database
                ↓
            Validation
                ↓
            Events/Jobs (async)
```

---

## 3. Database Schema

### Primary Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `events` | Core event data | `id`, `title`, `start_date`, `price`, `status` |
| `event_attendees` | Who's attending | `event_id`, `user_id`, `status`, `paid_at` |
| `event_payments` | Payment records | `event_id`, `user_id`, `stripe_id`, `amount` |

### Relationships
```
users ─────┬───── events (organizer)
           │
           └───── event_attendees ───── events
                         │
                         └───── event_payments
```

### Important Constraints
- `events.status` ENUM: `draft`, `published`, `cancelled`, `completed`
- `event_attendees.status` ENUM: `pending`, `confirmed`, `cancelled`, `refunded`
- Unique constraint: `(event_id, user_id)` on `event_attendees`

---

## 4. API Endpoints

### Existing Endpoints
| Method | Endpoint | Purpose | Controller Method |
|--------|----------|---------|-------------------|
| GET | `/api/events` | List events | `EventController@index` |
| POST | `/api/events` | Create event | `EventController@store` |
| GET | `/api/events/{id}` | Get event | `EventController@show` |
| PUT | `/api/events/{id}` | Update event | `EventController@update` |
| DELETE | `/api/events/{id}` | Cancel event | `EventController@destroy` |

### Authentication Requirements
- All endpoints require Bearer token
- Organizer-only actions: `store`, `update`, `destroy`
- Attendee actions: `attend`, `cancel-attendance`

---

## 5. External Integrations

### Stripe (Payments)
- **Config:** `config/services.php` → `stripe`
- **Service:** `app/Services/StripeService.php`
- **Webhooks:** `app/Http/Controllers/Webhooks/StripeController.php`
- **Events handled:** `payment_intent.succeeded`, `refund.created`

### Email Notifications
- **Mailables:** `app/Mail/EventReminder.php`, `app/Mail/EventCancelled.php`
- **Triggered by:** Event listeners in `app/Listeners/`

---

## 6. Common Tasks (How-To)

### "I need to add a field to events"
1. Create migration: `php artisan make:migration add_[field]_to_events_table`
2. Update model: Add to `$fillable` in `app/Models/Event.php`
3. Update API: Add validation in `app/Http/Requests/EventRequest.php`
4. Update tests: Add coverage in `tests/Feature/EventTest.php`

### "I need to add a new event action"
1. Add route in `routes/api.php`
2. Add controller method in `EventController.php`
3. Add business logic in `EventService.php`
4. Add event/listener if async needed

### "I need to understand the payment flow"
1. Start at `EventController@attend`
2. Follow to `EventService@processAttendance`
3. See Stripe call in `StripeService@createPaymentIntent`
4. Webhook handling in `StripeController@handlePaymentSuccess`

---

## 7. Testing

### Test Files
| File | What It Tests |
|------|---------------|
| `tests/Feature/EventTest.php` | API endpoints |
| `tests/Unit/EventServiceTest.php` | Business logic |
| `tests/Unit/EventModelTest.php` | Model methods |

### Running Tests
```bash
# All event tests
php artisan test --filter=Event

# Specific test
php artisan test --filter=EventTest::test_user_can_create_event
```

### Test Fixtures
- Located in: `tests/Fixtures/events.json`
- Factory: `database/factories/EventFactory.php`

---

## 8. Known Issues & Technical Debt

- [ ] **Issue:** [Description of known issue]
- [ ] **Debt:** [Technical debt that should be addressed]
- [ ] **TODO:** [Planned improvement]

---

## 9. Related Domains

| Domain | Relationship | Context File |
|--------|--------------|--------------|
| Payments | Events trigger payments | `domain-contexts/payments.md` |
| Notifications | Events send notifications | `domain-contexts/notifications.md` |
| Users | Events have organizers/attendees | `domain-contexts/users.md` |

---

> ⚠️ **When working in this domain:** Always read this file first, then check the Infrastructure Analysis if one exists for your current feature.

