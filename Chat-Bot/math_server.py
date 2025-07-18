from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")



@mcp.tool()
def add(a: int, b: int) -> int:
    """Adds two integers.
    Args:
        a (int): First integer.
        b (int): Second integer.
    Returns:
        int: The sum of the two integers.
    """
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiplies two integers.
    Args:
        a (int): First integer.
        b (int): Second integer.
    Returns:
        int: The product of the two integers.
    """
    return a * b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtracts the second integer from the first.
    Args:
        a (int): First integer.
        b (int): Second integer.
    Returns:
        int: The result of subtracting b from a.
    """
    return a - b

@mcp.tool()
def modulo(a: int, b: int) -> int:
    """Calculates the modulo of two integers.
    Args:
        a (int): The dividend.
        b (int): The divisor.
    Returns:
        int: The remainder of the division of a by b.
    """
    return a % b

@mcp.tool()
def premOper(a: int, b: int) -> int:
    """Performs a custom operation on two integers.
    Args:
        a (int): First integer.
        b (int): Second integer.
    Returns:
        int: The result of the operation, defined as a + 2*b.
    """
    return a + 2*b

if __name__ == "__main__":
    mcp.run(transport="stdio")