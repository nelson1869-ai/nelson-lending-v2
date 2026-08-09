"""Constants for the notifications and transactional outbox module."""

# Outbox Statuses
OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_DELIVERED = "delivered"
OUTBOX_STATUS_FAILED = "failed"
OUTBOX_STATUS_DEAD_LETTER = "dead_letter"

ALL_OUTBOX_STATUSES = {
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_FAILED,
    OUTBOX_STATUS_DEAD_LETTER,
}

# Channels
CHANNEL_IN_APP = "in_app"
ALL_CHANNELS = {
    CHANNEL_IN_APP,
}

# Recipient Types
RECIPIENT_TYPE_BORROWER = "borrower"
RECIPIENT_TYPE_OWNER = "owner"

ALL_RECIPIENT_TYPES = {
    RECIPIENT_TYPE_BORROWER,
    RECIPIENT_TYPE_OWNER,
}

# Template Keys
TEMPLATE_BORROWER_REGISTRATION_APPROVED = "borrower_registration_approved"
TEMPLATE_LOAN_REQUEST_SUBMITTED = "loan_request_submitted"
TEMPLATE_LOAN_REQUEST_APPROVED = "loan_request_approved"
TEMPLATE_LOAN_REQUEST_REJECTED = "loan_request_rejected"
TEMPLATE_LOAN_DISBURSED = "loan_disbursed"
TEMPLATE_PAYMENT_RECEIVED = "payment_received"

ALL_TEMPLATE_KEYS = {
    TEMPLATE_BORROWER_REGISTRATION_APPROVED,
    TEMPLATE_LOAN_REQUEST_SUBMITTED,
    TEMPLATE_LOAN_REQUEST_APPROVED,
    TEMPLATE_LOAN_REQUEST_REJECTED,
    TEMPLATE_LOAN_DISBURSED,
    TEMPLATE_PAYMENT_RECEIVED,
}

# Every persisted payload carries an explicit version so queued records remain
# renderable after template payloads evolve.
PAYLOAD_SCHEMA_VERSION = 1

EVENT_TYPE_BY_TEMPLATE = {
    TEMPLATE_BORROWER_REGISTRATION_APPROVED: "borrower_registration_approved",
    TEMPLATE_LOAN_REQUEST_SUBMITTED: "loan_request_submitted",
    TEMPLATE_LOAN_REQUEST_APPROVED: "loan_request_approved",
    TEMPLATE_LOAN_REQUEST_REJECTED: "loan_request_rejected",
    TEMPLATE_LOAN_DISBURSED: "loan_disbursed",
    TEMPLATE_PAYMENT_RECEIVED: "payment_received",
}

REQUIRED_PAYLOAD_FIELDS = {
    TEMPLATE_BORROWER_REGISTRATION_APPROVED: {"borrower_id", "first_name", "last_name"},
    TEMPLATE_LOAN_REQUEST_SUBMITTED: {"loan_request_id", "requested_principal"},
    TEMPLATE_LOAN_REQUEST_APPROVED: {"loan_request_id", "requested_principal"},
    TEMPLATE_LOAN_REQUEST_REJECTED: {
        "loan_request_id",
        "requested_principal",
        "rejection_reason",
    },
    TEMPLATE_LOAN_DISBURSED: {"loan_id", "original_principal"},
    TEMPLATE_PAYMENT_RECEIVED: {"payment_id", "loan_id", "amount", "payment_date"},
}
