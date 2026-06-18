# User Roles

## Purpose
Define all user types that interact with the TalentNyk platform — both internal team members and external network participants.

## Internal Team Roles

### Platform Administrator
- Full system access
- User management, permissions, configuration
- Audit log review

### Proposal Manager
- Solicitation review and bid/no-bid decisions
- Vendor selection from matched recommendations
- Proposal narrative review and approval
- Final submission authority

### Compliance Officer
- Agreement template management
- Regulatory compliance verification
- SBA certification tracking
- Exclusivity conflict checks

### Financial Controller
- Cash flow monitoring
- AR factoring decisions
- Payment routing approval
- Bank account management

### Network Coordinator
- Vendor onboarding and relationship management
- License/certification verification
- Past performance snippet collection
- Vendor communication

## External User Roles

### Vendor (Service Partner)
- Onboarding wizard (self-service profile creation)
- Document signing (agreements, task-specific TAs)
- Pricing matrix updates
- Post-award: invoice submission, performance logs
- **Portal access:** Limited to own data

### Individual Specialist (Contingent Worker)
- Profile and resume management
- Contingent offer letter acceptance
- Letter of commitment signing
- Post-award: time tracking, onboarding documents

### Manufacturer Partner
- Product catalog and capability profile
- Pricing and capacity updates
- Agreement signing
- Post-award: shipping confirmation, MIL-STD-129 label access

## Access Control Principles

- External users see only their own data, agreements, and assigned bids
- Internal roles follow least-privilege by function
- All agreement actions require authenticated digital signature
- Audit trail captures every user action on compliance-relevant data

## Dependencies
- [[architecture-diagram]]
- [[../12-platform-admin/internal-team-management]]
- [[../12-platform-admin/vendor-portal]]

## Key Rules & Compliance
- Digital signatures must be legally binding under ESIGN Act
- Vendor access to bid data controlled by NDA acceptance

## Open Questions
- SSO or email/password auth?
- Role-based (RBAC) or attribute-based (ABAC) access control?
