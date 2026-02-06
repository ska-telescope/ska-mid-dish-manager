## Test Structure

### Test Independence
- Each test runs independently without relying on execution order
- Devices are automatically reset between transition tests via the `setup_and_teardown` fixture
- Tests marked with `@pytest.mark.transition` and `@pytest.mark.movement` depend on the `setup_and_teardown` fixture and/or require time to reach the desired state
- Other tests focus on event verification and attribute read/write operations

### Shared Resources
- All tests use the same device proxy client (provided by a package-scoped fixture)

### Event Subscription Management
- Tests automatically clean up event subscriptions using `setup_subscriptions` and `remove_subscriptions` helper methods
- **Important**: If you manually create subscriptions in a test, ensure they are removed before the test completes

### Troubleshooting
- **Missing event errors**: These are acceptable transient failures - simply re-run the test
- **Other failures**: Must be investigated and fixed
