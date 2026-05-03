"""Example usage of JWT authentication module for Loom MCP.

This script demonstrates:
1. Creating tokens for different user roles
2. Validating tokens and extracting claims
3. Checking tool access based on roles
4. Getting token information
"""

import os
import sys
from datetime import UTC, datetime

# Set up JWT secret for this example
os.environ["LOOM_JWT_SECRET"] = "example-secret-key-change-in-production"

# Import JWT auth functions
try:
    from loom.jwt_auth import (
        create_token,
        validate_token,
        check_tool_access,
        get_token_info,
        verify_and_get_role,
        get_allowed_tools,
        ROLE_PERMISSIONS,
    )
except ImportError:
    print("Error: jwt_auth module not found. Make sure Loom is installed.")
    sys.exit(1)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def example_1_token_generation() -> None:
    """Example 1: Generate tokens for different roles."""
    print_header("Example 1: Token Generation")

    # Create admin token (24-hour expiry)
    admin_token = create_token("admin@loom.dev", "admin", expires_in_hours=24)
    print(f"\nAdmin Token (24h expiry):")
    print(f"  User ID: admin@loom.dev")
    print(f"  Role: admin")
    print(f"  Token: {admin_token[:50]}...")

    # Create researcher token (7-day expiry)
    researcher_token = create_token("researcher@loom.dev", "researcher", expires_in_hours=168)
    print(f"\nResearcher Token (7 day expiry):")
    print(f"  User ID: researcher@loom.dev")
    print(f"  Role: researcher")
    print(f"  Token: {researcher_token[:50]}...")

    # Create red team token (8-hour expiry)
    red_team_token = create_token("tester@loom.dev", "red_team", expires_in_hours=8)
    print(f"\nRed Team Token (8h expiry):")
    print(f"  User ID: tester@loom.dev")
    print(f"  Role: red_team")
    print(f"  Token: {red_team_token[:50]}...")

    # Create viewer token (30-day expiry)
    viewer_token = create_token("observer@loom.dev", "viewer", expires_in_hours=720)
    print(f"\nViewer Token (30 day expiry):")
    print(f"  User ID: observer@loom.dev")
    print(f"  Role: viewer")
    print(f"  Token: {viewer_token[:50]}...")

    return {
        "admin": admin_token,
        "researcher": researcher_token,
        "red_team": red_team_token,
        "viewer": viewer_token,
    }


def example_2_token_validation(tokens: dict[str, str]) -> None:
    """Example 2: Validate tokens and extract claims."""
    print_header("Example 2: Token Validation")

    # Validate admin token
    print("\nValidating Admin Token:")
    payload = validate_token(tokens["admin"])
    print(f"  User ID: {payload['sub']}")
    print(f"  Role: {payload['role']}")
    print(f"  Issued at: {datetime.fromtimestamp(payload['iat'], tz=UTC).isoformat()}")
    print(f"  Expires at: {datetime.fromtimestamp(payload['exp'], tz=UTC).isoformat()}")

    # Validate researcher token
    print("\nValidating Researcher Token:")
    payload = validate_token(tokens["researcher"])
    print(f"  User ID: {payload['sub']}")
    print(f"  Role: {payload['role']}")
    print(f"  Valid: Yes")


def example_3_role_based_access(tokens: dict[str, str]) -> None:
    """Example 3: Check tool access based on roles."""
    print_header("Example 3: Role-Based Tool Access")

    # Test tools for different roles
    test_tools = [
        "research_fetch",      # Safe tool
        "search",              # Safe tool
        "llm",                 # Safe tool
        "prompt_reframe",      # Restricted tool
        "adversarial_debate",  # Restricted tool
        "context_poison",      # Restricted tool
    ]

    roles = ["admin", "researcher", "red_team", "viewer"]

    print("\nTool Access Matrix:")
    print(f"\n{'Tool':<30} {'Admin':<10} {'Researcher':<15} {'Red Team':<12} {'Viewer':<10}")
    print("-" * 80)

    for tool in test_tools:
        access = []
        for role in roles:
            token = tokens[role]
            allowed = check_tool_access(token, tool)
            access.append("✓" if allowed else "✗")

        tool_display = tool[:28]
        print(f"{tool_display:<30} {access[0]:<10} {access[1]:<15} {access[2]:<12} {access[3]:<10}")


def example_4_token_information(tokens: dict[str, str]) -> None:
    """Example 4: Get detailed token information."""
    print_header("Example 4: Token Information")

    for role_name, token in tokens.items():
        info = get_token_info(token)
        print(f"\n{role_name.upper()} Token:")
        print(f"  User ID: {info['user_id']}")
        print(f"  Role: {info['role']}")
        print(f"  Issued at: {info['issued_at']}")
        print(f"  Expires at: {info['expires_at']}")
        print(f"  Is expired: {info['is_expired']}")
        print(f"  Allowed tools: {info['allowed_tools_count']}")
        print(f"  Categories: {', '.join(info['allowed_tool_categories'])}")


def example_5_role_permissions() -> None:
    """Example 5: Display role permission matrix."""
    print_header("Example 5: Role Permission Matrix")

    print("\nRole Permissions Overview:")
    for role, permissions in ROLE_PERMISSIONS.items():
        print(f"\n{role.upper()}:")
        if "*" in permissions:
            print("  Access: UNRESTRICTED (all tools)")
        else:
            print(f"  Access: {len(permissions)} specific tools")
            # Show first 5 tools
            tools_list = list(permissions)[:5]
            for tool in tools_list:
                print(f"    - {tool}")
            if len(permissions) > 5:
                print(f"    ... and {len(permissions) - 5} more")


def example_6_verify_and_get_role(tokens: dict[str, str]) -> None:
    """Example 6: Convenience function for role extraction."""
    print_header("Example 6: Extract Role from Token")

    print("\nExtracting roles from tokens:")
    for role_name, token in tokens.items():
        role = verify_and_get_role(token)
        print(f"  {role_name:<15} -> {role}")


def example_7_allowed_tools_per_role() -> None:
    """Example 7: List allowed tools for each role."""
    print_header("Example 7: Allowed Tools per Role")

    for role in ["admin", "researcher", "red_team", "viewer"]:
        allowed = get_allowed_tools(role)
        print(f"\n{role.upper()}:")
        if "*" in allowed:
            print("  Access: UNRESTRICTED")
        else:
            sorted_tools = sorted(allowed)
            print(f"  Total: {len(sorted_tools)} tools")
            for i, tool in enumerate(sorted_tools, 1):
                print(f"    {i:2}. {tool}")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  JWT AUTHENTICATION MODULE - EXAMPLES")
    print("=" * 70)

    try:
        # Example 1: Token generation
        tokens = example_1_token_generation()

        # Example 2: Token validation
        example_2_token_validation(tokens)

        # Example 3: Role-based access
        example_3_role_based_access(tokens)

        # Example 4: Token information
        example_4_token_information(tokens)

        # Example 5: Role permissions
        example_5_role_permissions()

        # Example 6: Role extraction
        example_6_verify_and_get_role(tokens)

        # Example 7: Allowed tools
        example_7_allowed_tools_per_role()

        print("\n" + "=" * 70)
        print("  All examples completed successfully!")
        print("=" * 70 + "\n")

    except ImportError as e:
        print(f"\nError: {e}")
        print("\nMake sure PyJWT is installed:")
        print("  pip install PyJWT")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
