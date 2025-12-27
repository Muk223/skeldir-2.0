"""R3: Add webhook secret columns to tenants (required for webhook ingress).

The repository contains an older webhook-secret migration in a non-applied branch.
R3 requires webhook ingress to run end-to-end in a clean-room CI database, so we
apply these columns on the canonical head.
"""

from alembic import op
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "202512271910"
down_revision: Union[str, None] = "202512271900"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS shopify_webhook_secret TEXT")
    op.execute("ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS stripe_webhook_secret TEXT")
    op.execute("ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS paypal_webhook_secret TEXT")
    op.execute("ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS woocommerce_webhook_secret TEXT")

    op.execute(
        """
        COMMENT ON COLUMN public.tenants.shopify_webhook_secret IS
        'Tenant-scoped Shopify webhook signing secret. Used for HMAC verification.';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN public.tenants.stripe_webhook_secret IS
        'Tenant-scoped Stripe webhook signing secret. Used for signature verification.';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN public.tenants.paypal_webhook_secret IS
        'Tenant-scoped PayPal webhook signing secret. Used for signature verification.';
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN public.tenants.woocommerce_webhook_secret IS
        'Tenant-scoped WooCommerce webhook signing secret. Used for HMAC verification.';
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.tenants DROP COLUMN IF EXISTS woocommerce_webhook_secret")
    op.execute("ALTER TABLE public.tenants DROP COLUMN IF EXISTS paypal_webhook_secret")
    op.execute("ALTER TABLE public.tenants DROP COLUMN IF EXISTS stripe_webhook_secret")
    op.execute("ALTER TABLE public.tenants DROP COLUMN IF EXISTS shopify_webhook_secret")

