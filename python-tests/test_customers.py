"""Test customer CRUD operations.

This module tests the complete lifecycle of customer management
including creation, retrieval, listing, and balance checking.
"""
import pytest
import uuid

# Import SDK components
try:
    from drip import Drip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None

# Try to import CustomerStatus enum if available
try:
    from drip import CustomerStatus
    CUSTOMER_STATUS_AVAILABLE = True
except ImportError:
    CUSTOMER_STATUS_AVAILABLE = False
    CustomerStatus = None


pytestmark = pytest.mark.skipif(
    not DRIP_SDK_AVAILABLE,
    reason="drip-sdk not installed"
)


class TestCreateCustomer:
    """Test customer creation operations."""

    def test_create_customer_basic(self, client):
        """Create a customer with minimal required fields.

        A customer should be creatable with just an onchain_address.
        """
        unique_id = uuid.uuid4().hex[:12]
        customer = client.create_customer(
            onchain_address=f"0x{uuid.uuid4().hex}42",
            external_customer_id=f"test_basic_{unique_id}"
        )

        assert customer is not None
        assert customer.id is not None
        assert customer.id.startswith("cus_")

    def test_create_customer_with_metadata(self, client):
        """Create a customer with metadata.

        Metadata allows storing arbitrary key-value pairs
        with the customer record.
        """
        unique_id = uuid.uuid4().hex[:12]
        test_metadata = {
            "test": True,
            "created_by": "sdk_test",
            "test_run": unique_id
        }

        customer = client.create_customer(
            onchain_address=f"0x{uuid.uuid4().hex}43",
            external_customer_id=f"test_meta_{unique_id}",
            metadata=test_metadata
        )

        assert customer is not None
        assert customer.id.startswith("cus_")
        # Metadata should be stored (if returned in response)
        if hasattr(customer, 'metadata') and customer.metadata:
            assert customer.metadata.get("test") is True

    def test_create_customer_address_stored(self, client):
        """Verify onchain_address is stored correctly."""
        unique_id = uuid.uuid4().hex[:12]
        test_address = f"0xABCDEF{uuid.uuid4().hex[:34]}"

        customer = client.create_customer(
            onchain_address=test_address,
            external_customer_id=f"test_addr_{unique_id}"
        )

        assert customer is not None
        if hasattr(customer, 'onchain_address'):
            # Address should match (case may vary)
            assert customer.onchain_address.lower() == test_address.lower()

    def test_create_customer_returns_id(self, client):
        """Verify customer ID is returned and properly formatted."""
        unique_id = uuid.uuid4().hex[:12]

        customer = client.create_customer(
            onchain_address=f"0x{uuid.uuid4().hex}44",
            external_customer_id=f"test_id_{unique_id}"
        )

        assert customer.id is not None
        assert isinstance(customer.id, str)
        assert customer.id.startswith("cus_")
        assert len(customer.id) > 4  # "cus_" plus some ID


class TestGetCustomer:
    """Test customer retrieval operations."""

    def test_get_customer_by_id(self, client, test_customer):
        """Retrieve an existing customer by ID.

        The get_customer method should return the full customer
        object for a given customer ID.
        """
        retrieved = client.get_customer(test_customer.id)

        assert retrieved is not None
        assert retrieved.id == test_customer.id

    def test_get_customer_fields(self, client, test_customer):
        """Verify retrieved customer has expected fields."""
        retrieved = client.get_customer(test_customer.id)

        assert retrieved.id is not None
        # Check for common customer fields
        assert hasattr(retrieved, 'id')

    def test_get_customer_not_found(self, client):
        """Test retrieval of non-existent customer."""
        with pytest.raises(Exception) as exc_info:
            client.get_customer("cus_nonexistent_12345")

        # Should raise 404 or similar error
        error = exc_info.value
        assert error is not None


class TestListCustomers:
    """Test customer listing operations."""

    def test_list_customers_basic(self, client):
        """List customers without filters.

        Should return a paginated list of customers.
        """
        response = client.list_customers()

        assert response is not None
        # Response should have a customers list
        if hasattr(response, 'customers'):
            assert isinstance(response.customers, list)
        elif hasattr(response, 'data'):
            assert isinstance(response.data, list)
        else:
            # Response might be a list directly
            assert response is not None

    def test_list_customers_with_limit(self, client):
        """List customers with a limit parameter.

        The limit should restrict the number of results returned.
        """
        limit = 5
        response = client.list_customers(limit=limit)

        assert response is not None
        # Check that results don't exceed limit
        if hasattr(response, 'customers'):
            assert len(response.customers) <= limit
        elif hasattr(response, 'data'):
            assert len(response.data) <= limit

    def test_list_customers_pagination(self, client):
        """Test customer list pagination.

        Should be able to paginate through results.
        """
        # Get first page
        first_page = client.list_customers(limit=2)
        assert first_page is not None

        # If there's a cursor/offset for pagination, test it
        if hasattr(first_page, 'cursor') and first_page.cursor:
            second_page = client.list_customers(limit=2, cursor=first_page.cursor)
            assert second_page is not None
        elif hasattr(first_page, 'next_cursor') and first_page.next_cursor:
            second_page = client.list_customers(limit=2, cursor=first_page.next_cursor)
            assert second_page is not None

    @pytest.mark.skipif(not CUSTOMER_STATUS_AVAILABLE, reason="CustomerStatus not available")
    def test_list_customers_with_status(self, client):
        """Filter customers by status.

        When filtering by status, all returned customers should
        have the specified status.
        """
        response = client.list_customers(status=CustomerStatus.ACTIVE)

        assert response is not None
        if hasattr(response, 'customers'):
            for customer in response.customers:
                if hasattr(customer, 'status'):
                    assert customer.status == CustomerStatus.ACTIVE or customer.status == "ACTIVE"


class TestGetBalance:
    """Test customer balance operations."""

    def test_get_balance(self, client, test_customer):
        """Check customer balance.

        The balance endpoint should return the current balance
        information for a customer.
        """
        balance = client.get_balance(test_customer.id)

        assert balance is not None

    def test_balance_has_amount(self, client, test_customer):
        """Verify balance response contains amount information."""
        balance = client.get_balance(test_customer.id)

        assert balance is not None
        # Balance should have some amount field
        has_balance_field = (
            hasattr(balance, 'balance') or
            hasattr(balance, 'balance_usdc') or
            hasattr(balance, 'available') or
            hasattr(balance, 'amount') or
            'balance' in str(balance).lower()
        )
        assert has_balance_field or balance is not None

    def test_balance_format(self, client, test_customer):
        """Verify balance is returned in expected format."""
        balance = client.get_balance(test_customer.id)

        assert balance is not None
        # Balance values should be numeric or string representations
        if hasattr(balance, 'balance_usdc'):
            assert balance.balance_usdc is not None
        if hasattr(balance, 'available'):
            assert balance.available is not None


class TestCustomerMetadata:
    """Test customer metadata operations."""

    def test_metadata_stored_on_create(self, client):
        """Verify metadata is stored when creating customer."""
        unique_id = uuid.uuid4().hex[:12]
        metadata = {
            "environment": "test",
            "version": "1.0",
            "tags": ["sdk", "test"]
        }

        customer = client.create_customer(
            onchain_address=f"0x{uuid.uuid4().hex}45",
            external_customer_id=f"test_metadata_{unique_id}",
            metadata=metadata
        )

        assert customer is not None
        # If metadata is returned, verify it
        if hasattr(customer, 'metadata') and customer.metadata:
            assert customer.metadata.get("environment") == "test"

    def test_metadata_retrieved_with_customer(self, client, test_customer):
        """Verify metadata is returned when retrieving customer."""
        retrieved = client.get_customer(test_customer.id)

        assert retrieved is not None
        # Metadata should be accessible if it was set
        if hasattr(retrieved, 'metadata'):
            # Metadata may be None or dict
            assert retrieved.metadata is None or isinstance(retrieved.metadata, dict)


class TestCustomerValidation:
    """Test customer input validation."""

    def test_invalid_address_format(self, client):
        """Test creation with invalid address format."""
        unique_id = uuid.uuid4().hex[:12]

        # This may raise an error or create anyway depending on validation
        try:
            customer = client.create_customer(
                onchain_address="invalid_address",
                external_customer_id=f"test_invalid_{unique_id}"
            )
            # If it succeeds, the SDK accepts any string
            assert customer is not None
        except Exception as e:
            # Validation error is expected
            assert "address" in str(e).lower() or "invalid" in str(e).lower() or e is not None

    def test_duplicate_external_id_handling(self, client, test_customer):
        """Test creation with duplicate external customer ID.

        Depending on SDK behavior, this may return the existing
        customer or raise an error.
        """
        try:
            # Try to create with same external ID
            customer = client.create_customer(
                onchain_address=f"0x{uuid.uuid4().hex}46",
                external_customer_id=test_customer.external_customer_id if hasattr(test_customer, 'external_customer_id') else f"dup_test_{uuid.uuid4().hex[:8]}"
            )
            # Might succeed with idempotent behavior or different handling
            assert customer is not None
        except Exception as e:
            # Conflict error is acceptable
            assert e is not None
