# API Test Framework - Core Module

## 📁 Structure

```
tests/
├── core/                          # ✅ Generic framework (reusable)
│   ├── __init__.py
│   ├── api_test_base.py          # Generic base class for ALL API tests
│   ├── step_executor.py          # Generic Allure step management
│   └── README.md                  # This file
│
├── jwt_auth_base.py              # JWT-specific base (extends APITestBase)
├── test_jwt_auth.py              # JWT auth tests
│
├── test_user_management.py       # Future: User API tests (uses APITestBase)
├── test_orders.py                # Future: Order API tests (uses APITestBase)
├── test_products.py              # Future: Product API tests (uses APITestBase)
│
└── conftest.py                   # Pytest configuration
```

---

## 🎯 Purpose

The `core/` folder contains **generic, reusable framework code** that ALL API tests can use.

### Why This Matters:

- ✅ **Single source of truth** for HTTP methods, validation, and logging
- ✅ **DRY principle** - Write once, use everywhere
- ✅ **Consistency** - All tests use the same patterns
- ✅ **Maintainability** - Update framework logic in one place
- ✅ **Scalability** - Easy to add new API endpoint tests

---

## 🔧 APITestBase - The Foundation

`api_test_base.py` provides the **generic base class** that ALL API tests inherit from.

### Features:

#### 1. **HTTP Methods** (Automatic Allure Logging)
- `await self.get(endpoint, headers, params)`
- `await self.post(endpoint, headers, body)`
- `await self.put(endpoint, headers, body)`
- `await self.patch(endpoint, headers, body)`
- `await self.delete(endpoint, headers)`
- `await self.head(endpoint, headers, params)`
- `await self.options(endpoint, headers)`

#### 2. **Response Validators**
- `self.assert_success_response(response, [200, 201])`
- `self.assert_error_response(response, [400, 401])`
- `self.assert_response_code_in(response, [200, 400, 503])`
- `self.assert_field_in_response(response, "field_name")`

#### 3. **Helpers**
- `self.parse_json_safe(response)` - Safe JSON parsing with fallback

#### 4. **Allure Logging** (Automatic)
- Request logging (method, endpoint, headers, body)
- Response logging (status, body)
- Assertion logging (expected, actual, result)

#### 5. **Step Executor** (NEW!)
- `self.step` - Generic Allure step manager available in ALL tests
- See [StepExecutor Section](#-stepexecutor---centralized-allure-steps) below

---

## 🎬 StepExecutor - Centralized Allure Steps

`step_executor.py` provides the **generic step executor** that centralizes ALL `allure.step()` usage.

### Why StepExecutor?

- ✅ **Single source of truth** for all Allure step creation
- ✅ **Consistent naming** across entire test suite
- ✅ **Reusable step patterns** (retry, iteration, conditional, etc.)
- ✅ **Easy customization** - Change step format globally in one place
- ✅ **Reduces boilerplate** - No more `with allure.step()` everywhere

### Available via `self.step` in ALL Tests:

#### HTTP Steps (Automatic):
```python
with self.step.http_get(endpoint):
    # GET request code

with self.step.http_post(endpoint):
    # POST request code

# Also: http_put, http_patch, http_delete, http_head, http_options
```

#### Validation Steps:
```python
with self.step.validate_response("Verify user created"):
    self.assert_success_response(response)

with self.step.validate_status_code([200, 201]):
    assert response.status_code in [200, 201]

with self.step.validate_field("user_id"):
    assert "user_id" in data
```

#### Custom Steps:
```python
with self.step.custom("Extract user ID from response"):
    user_id = response.json()["user_id"]

with self.step.action("Create", "new user"):
    # Creation logic

with self.step.action("Verify", "token generated"):
    # Verification logic
```

#### Loop/Iteration Steps:
```python
for i in range(3):
    with self.step.iteration(i, 3, "Request token"):
        response = await self.post(...)
```

#### Retry Steps:
```python
for attempt in range(max_retries):
    with self.step.retry(attempt, max_retries, "Connect to API"):
        try:
            response = await self.get(...)
            break
        except:
            continue
```

#### Conditional Steps:
```python
with self.step.conditional("User exists", user_exists):
    if user_exists:
        # Update user
    else:
        # Create user
```

#### Database/External Service Steps:
```python
with self.step.database_operation("Query", "users"):
    result = db.query("SELECT * FROM users")

with self.step.external_service_call("Payment Gateway", "Process payment"):
    payment_result = gateway.process(...)
```

#### Performance Measurement:
```python
import time
with self.step.measure_time("API response time"):
    start = time.time()
    response = await self.post(...)
    elapsed = time.time() - start
```

### @auto_step Decorator:

Automatically wrap functions as Allure steps:

```python
from .core.step_executor import auto_step

@auto_step("Authenticate user")
async def authenticate(self, username, password):
    # This entire function becomes an Allure step
    return await self.post("/auth/login", body={...})

@auto_step()  # Uses function name as step name
def extract_token(self, response):
    return response.json()["token"]
```

### See Also:
- `EXAMPLE_using_step_executor.py` - Comprehensive examples of all step types

---

## 📖 Usage Patterns

### Pattern 1: Direct Inheritance (Simple)

```python
from .core.api_test_base import APITestBase

class TestUserAPI(APITestBase):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.base_url = "https://api.example.com"
        cls.endpoint = "/users"

    async def test_create_user(self):
        headers = {"Content-Type": "application/json"}
        body = {"name": "John", "email": "john@example.com"}

        response = await self.post(self.endpoint, headers=headers, body=body)

        self.assert_success_response(response, [201])
        user_id = self.assert_field_in_response(response, "user_id")
```

### Pattern 2: Domain-Specific Base Class (Advanced)

```python
from .core.api_test_base import APITestBase

class JWTAuthTestBase(APITestBase):
    """JWT-specific base class with custom helpers"""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        from .test_jwt_auth import BASE_URL, JWT_ENDPOINT
        cls.base_url = BASE_URL
        cls.endpoint = JWT_ENDPOINT

    # Custom JWT-specific helper methods
    def build_auth_headers(self, user_id, phone_number):
        return {"userId": user_id, "phoneNumber": phone_number}

    def assert_token_in_response(self, response):
        # JWT-specific validation logic
        pass
```

Then your tests inherit from the domain-specific base:

```python
from .jwt_auth_base import JWTAuthTestBase

class TestJWTAuth(JWTAuthTestBase):
    async def test_valid_credentials(self):
        headers = self.build_auth_headers("1001", "5550000001")
        response = await self.post(self.endpoint, headers=headers)
        token = self.assert_token_in_response(response)
```

---

## 🏗️ Architecture: Java BaseServiceHelper Pattern

This design mirrors Java's `BaseServiceHelper` pattern:

**Java Version:**
```java
public abstract class BaseServiceHelper {
    public Response postCall(String endpoint, Map headers) {
        // Centralized HTTP + logging
    }
    public Response validateResponse(Response response) {
        // Centralized validation
    }
}

public class AuthTests extends BaseServiceHelper {
    // Use inherited methods
}
```

**Python Equivalent:**
```python
class APITestBase:
    async def post(self, endpoint, headers):
        # Centralized HTTP + logging

    def assert_success_response(self, response):
        # Centralized validation

class TestAuth(APITestBase):
    # Use inherited methods
```

---

## 📊 Code Reduction Example

**Before (Without Framework):**
```python
async def test_create_user(self):
    with allure.step("Send POST request"):
        log_api_request("POST", "/users", headers=headers)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/users",
                headers=headers,
                json=body,
                timeout=10.0
            )

        log_api_response(response.status_code, response.json())

    with allure.step("Validate response"):
        log_assertion("Status code is 201", 201, response.status_code)
        assert response.status_code == 201
        # ... more validation
```

**After (With Framework):**
```python
async def test_create_user(self):
    response = await self.post(self.endpoint, headers=headers, body=body)
    self.assert_success_response(response, [201])
    user_id = self.assert_field_in_response(response, "user_id")
```

**Result:** 67% less code, cleaner, more maintainable!

---

## 🚀 Adding New API Tests

### Step 1: Choose Your Approach

**Option A: Use APITestBase directly** (for simple endpoints)
```python
from .core.api_test_base import APITestBase

class TestOrderAPI(APITestBase):
    # Set base_url and endpoint in setup_class
```

**Option B: Create domain-specific base** (for complex domains with custom helpers)
```python
from .core.api_test_base import APITestBase

class OrderAPITestBase(APITestBase):
    # Add order-specific helpers
    def build_order_payload(self, items):
        # Custom logic
        pass
```

### Step 2: Write Your Tests

```python
class TestOrderAPI(OrderAPITestBase):
    async def test_create_order(self):
        response = await self.post(...)
        self.assert_success_response(response)
```

---

## 🎨 Customization

### Adding New Validators

Edit `api_test_base.py`:

```python
def assert_pagination(self, response, expected_page_size):
    """Validate pagination metadata"""
    data = self.parse_json_safe(response)

    assert "pagination" in data
    assert data["pagination"]["page_size"] == expected_page_size
```

---

## 🛡️ Best Practices

1. **Never modify existing generic methods** - They're used by all tests
2. **Create domain-specific base classes** for specialized helpers
3. **Keep APITestBase generic** - No endpoint-specific logic
4. **Document custom validators** with clear examples
5. **Follow the inheritance chain**: APITestBase → DomainBase → TestClass

---

## 📚 Examples

See `tests/EXAMPLE_future_api_test.py` for comprehensive examples of:
- Direct APITestBase usage
- Creating domain-specific base classes
- Custom validators
- Query parameters
- Different HTTP methods

---

## 🔄 Migration Guide

**Migrating existing tests to use the framework:**

1. **Identify endpoint** (e.g., `/auth/login`)
2. **Create base class** (or use APITestBase directly)
3. **Set base_url and endpoint** in `setup_class()`
4. **Replace manual HTTP calls** with `self.post()`, `self.get()`, etc.
5. **Replace manual validations** with `self.assert_success_response()`, etc.
6. **Remove manual Allure logging** (framework handles it)

---

## 📞 Support

For questions or issues with the framework:
- Check `EXAMPLE_future_api_test.py` for examples
- Review existing tests like `test_jwt_auth.py`
- Refer to inline documentation in `api_test_base.py`

---

**Last Updated:** December 2024
**Maintained By:** pytest API harness Team
