# AI Logistics Rules

Always work one file at a time.

Never redesign architecture.

Never modify unrelated files.

Architecture:

Router
↓

Service
↓

Repository
↓

Models

Repositories contain SQL only.

Services contain business logic.

Routers contain dependency injection only.

Use SQLAlchemy 2.0.

Use Pydantic v2.

Use Dependency Injection.

Never use session.query().

Always use select().

Always preserve existing architecture.

Review generated code before moving to next file.

Never introduce circular imports.

Never rewrite working code.

Always make minimal safe changes.