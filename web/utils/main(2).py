"""Absolute Value."""


def abs_val(num: float) -> float:
    """
    Find the absolute value of a number.

    >>> abs_val(-5.1)
    5.1
    >>> abs_val(-5) == abs_val(5)
    True
    >>> abs_val(0)
    0
    """
    return -num if num < 0 else num


def abs_min(x: list[int]) -> int:
    """
    >>> abs_min([0,5,1,11])
    0
    >>> abs_min([3,-10,-2])
    -2
    >>> abs_min([])
    Traceback (most recent call last):
        ...
    ValueError: abs_min() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_min() arg is an empty sequence")
    j = x[0]
    for i in x:
        if abs_val(i) < abs_val(j):
            j = i
    return j


def abs_max(x: list[int]) -> int:
    """
    >>> abs_max([0,5,1,11])
    11
    >>> abs_max([3,-10,-2])
    -10
    >>> abs_max([])
    Traceback (most recent call last):
        ...
    ValueError: abs_max() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_max() arg is an empty sequence")
    j = x[0]
    for i in x:
        if abs(i) > abs(j):
            j = i
    return j


def abs_max_sort(x: list[int]) -> int:
    """
    >>> abs_max_sort([0,5,1,11])
    11
    >>> abs_max_sort([3,-10,-2])
    -10
    >>> abs_max_sort([])
    Traceback (most recent call last):
        ...
    ValueError: abs_max_sort() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_max_sort() arg is an empty sequence")
    return sorted(x, key=abs)[-1]


def test_abs_val():
    """
    >>> test_abs_val()
    """
    assert abs_val(0) == 0
    assert abs_val(34) == 34
    assert abs_val(-100000000000) == 100000000000

    a = [-3, -1, 2, -11]
    assert abs_max(a) == -11
    assert abs_max_sort(a) == -11
    assert abs_min(a) == -1

def allocation_num(number_of_bytes: int, partitions: int) -> list[str]:
    """
    Divide a number of bytes into x partitions.
    :param number_of_bytes: the total of bytes.
    :param partitions: the number of partition need to be allocated.
    :return: list of bytes to be assigned to each worker thread

    >>> allocation_num(16647, 4)
    ['1-4161', '4162-8322', '8323-12483', '12484-16647']
    >>> allocation_num(50000, 5)
    ['1-10000', '10001-20000', '20001-30000', '30001-40000', '40001-50000']
    >>> allocation_num(888, 999)
    Traceback (most recent call last):
        ...
    ValueError: partitions can not > number_of_bytes!
    >>> allocation_num(888, -4)
    Traceback (most recent call last):
        ...
    ValueError: partitions must be a positive number!
    """
    if partitions <= 0:
        raise ValueError("partitions must be a positive number!")
    if partitions > number_of_bytes:
        raise ValueError("partitions can not > number_of_bytes!")
    bytes_per_partition = number_of_bytes // partitions
    allocation_list = []
    for i in range(partitions):
        start_bytes = i * bytes_per_partition + 1
        end_bytes = (
            number_of_bytes if i == partitions - 1 else (i + 1) * bytes_per_partition
        )
        allocation_list.append(f"{start_bytes}-{end_bytes}")
    return allocation_list
def arc_length(angle: int, radius: int) -> float:
    """
    >>> arc_length(45, 5)
    3.9269908169872414
    >>> arc_length(120, 15)
    31.415926535897928
    >>> arc_length(90, 10)
    15.707963267948966
    """
    return 2 * pi * radius * (angle / 360)
def surface_area_cube(side_length: float) -> float:
    """
    Calculate the Surface Area of a Cube.

    >>> surface_area_cube(1)
    6
    >>> surface_area_cube(1.6)
    15.360000000000003
    >>> surface_area_cube(0)
    0
    >>> surface_area_cube(3)
    54
    >>> surface_area_cube(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cube() only accepts non-negative values
    """
    if side_length < 0:
        raise ValueError("surface_area_cube() only accepts non-negative values")
    return 6 * side_length**2


def surface_area_cuboid(length: float, breadth: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cuboid.

    >>> surface_area_cuboid(1, 2, 3)
    22
    >>> surface_area_cuboid(0, 0, 0)
    0
    >>> surface_area_cuboid(1.6, 2.6, 3.6)
    38.56
    >>> surface_area_cuboid(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    >>> surface_area_cuboid(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    >>> surface_area_cuboid(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    """
    if length < 0 or breadth < 0 or height < 0:
        raise ValueError("surface_area_cuboid() only accepts non-negative values")
    return 2 * ((length * breadth) + (breadth * height) + (length * height))


def surface_area_sphere(radius: float) -> float:
    """
    Calculate the Surface Area of a Sphere.
    Wikipedia reference: https://en.wikipedia.org/wiki/Sphere
    Formula: 4 * pi * r^2

    >>> surface_area_sphere(5)
    314.1592653589793
    >>> surface_area_sphere(1)
    12.566370614359172
    >>> surface_area_sphere(1.6)
    32.169908772759484
    >>> surface_area_sphere(0)
    0.0
    >>> surface_area_sphere(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_sphere() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("surface_area_sphere() only accepts non-negative values")
    return 4 * pi * radius**2


def surface_area_hemisphere(radius: float) -> float:
    """
    Calculate the Surface Area of a Hemisphere.
    Formula: 3 * pi * r^2

    >>> surface_area_hemisphere(5)
    235.61944901923448
    >>> surface_area_hemisphere(1)
    9.42477796076938
    >>> surface_area_hemisphere(0)
    0.0
    >>> surface_area_hemisphere(1.1)
    11.40398133253095
    >>> surface_area_hemisphere(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_hemisphere() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("surface_area_hemisphere() only accepts non-negative values")
    return 3 * pi * radius**2


def surface_area_cone(radius: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cone.
    Wikipedia reference: https://en.wikipedia.org/wiki/Cone
    Formula: pi * r * (r + (h ** 2 + r ** 2) ** 0.5)

    >>> surface_area_cone(10, 24)
    1130.9733552923256
    >>> surface_area_cone(6, 8)
    301.59289474462014
    >>> surface_area_cone(1.6, 2.6)
    23.387862992395807
    >>> surface_area_cone(0, 0)
    0.0
    >>> surface_area_cone(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    >>> surface_area_cone(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    >>> surface_area_cone(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    """
    if radius < 0 or height < 0:
        raise ValueError("surface_area_cone() only accepts non-negative values")
    return pi * radius * (radius + (height**2 + radius**2) ** 0.5)


def surface_area_conical_frustum(
    radius_1: float, radius_2: float, height: float
) -> float:
    """
    Calculate the Surface Area of a Conical Frustum.

    >>> surface_area_conical_frustum(1, 2, 3)
    45.511728065337266
    >>> surface_area_conical_frustum(4, 5, 6)
    300.7913575056268
    >>> surface_area_conical_frustum(0, 0, 0)
    0.0
    >>> surface_area_conical_frustum(1.6, 2.6, 3.6)
    78.57907060751548
    >>> surface_area_conical_frustum(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    >>> surface_area_conical_frustum(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    >>> surface_area_conical_frustum(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    """
    if radius_1 < 0 or radius_2 < 0 or height < 0:
        raise ValueError(
            "surface_area_conical_frustum() only accepts non-negative values"
        )
    slant_height = (height**2 + (radius_1 - radius_2) ** 2) ** 0.5
    return pi * ((slant_height * (radius_1 + radius_2)) + radius_1**2 + radius_2**2)


def surface_area_cylinder(radius: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cylinder.
    Wikipedia reference: https://en.wikipedia.org/wiki/Cylinder
    Formula: 2 * pi * r * (h + r)

    >>> surface_area_cylinder(7, 10)
    747.6990515543707
    >>> surface_area_cylinder(1.6, 2.6)
    42.22300526424682
    >>> surface_area_cylinder(0, 0)
    0.0
    >>> surface_area_cylinder(6, 8)
    527.7875658030853
    >>> surface_area_cylinder(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    >>> surface_area_cylinder(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    >>> surface_area_cylinder(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    """
    if radius < 0 or height < 0:
        raise ValueError("surface_area_cylinder() only accepts non-negative values")
    return 2 * pi * radius * (height + radius)


def surface_area_torus(torus_radius: float, tube_radius: float) -> float:
    """Calculate the Area of a Torus.
    Wikipedia reference: https://en.wikipedia.org/wiki/Torus
    :return 4pi^2 * torus_radius * tube_radius
    >>> surface_area_torus(1, 1)
    39.47841760435743
    >>> surface_area_torus(4, 3)
    473.7410112522892
    >>> surface_area_torus(3, 4)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() does not support spindle or self intersecting tori
    >>> surface_area_torus(1.6, 1.6)
    101.06474906715503
    >>> surface_area_torus(0, 0)
    0.0
    >>> surface_area_torus(-1, 1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() only accepts non-negative values
    >>> surface_area_torus(1, -1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() only accepts non-negative values
    """
    if torus_radius < 0 or tube_radius < 0:
        raise ValueError("surface_area_torus() only accepts non-negative values")
    if torus_radius < tube_radius:
        raise ValueError(
            "surface_area_torus() does not support spindle or self intersecting tori"
        )
    return 4 * pow(pi, 2) * torus_radius * tube_radius


def area_rectangle(length: float, width: float) -> float:
    """
    Calculate the area of a rectangle.

    >>> area_rectangle(10, 20)
    200
    >>> area_rectangle(1.6, 2.6)
    4.16
    >>> area_rectangle(0, 0)
    0
    >>> area_rectangle(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rectangle() only accepts non-negative values
    >>> area_rectangle(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rectangle() only accepts non-negative values
    >>> area_rectangle(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_rectangle() only accepts non-negative values
    """
    if length < 0 or width < 0:
        raise ValueError("area_rectangle() only accepts non-negative values")
    return length * width


def area_square(side_length: float) -> float:
    """
    Calculate the area of a square.

    >>> area_square(10)
    100
    >>> area_square(0)
    0
    >>> area_square(1.6)
    2.5600000000000005
    >>> area_square(-1)
    Traceback (most recent call last):
        ...
    ValueError: area_square() only accepts non-negative values
    """
    if side_length < 0:
        raise ValueError("area_square() only accepts non-negative values")
    return side_length**2


def area_triangle(base: float, height: float) -> float:
    """
    Calculate the area of a triangle given the base and height.

    >>> area_triangle(10, 10)
    50.0
    >>> area_triangle(1.6, 2.6)
    2.08
    >>> area_triangle(0, 0)
    0.0
    >>> area_triangle(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    >>> area_triangle(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    >>> area_triangle(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    """
    if base < 0 or height < 0:
        raise ValueError("area_triangle() only accepts non-negative values")
    return (base * height) / 2


def area_triangle_three_sides(side1: float, side2: float, side3: float) -> float:
    """
    Calculate area of triangle when the length of 3 sides are known.
    This function uses Heron's formula: https://en.wikipedia.org/wiki/Heron%27s_formula

    >>> area_triangle_three_sides(5, 12, 13)
    30.0
    >>> area_triangle_three_sides(10, 11, 12)
    51.521233486786784
    >>> area_triangle_three_sides(0, 0, 0)
    0.0
    >>> area_triangle_three_sides(1.6, 2.6, 3.6)
    1.8703742940919619
    >>> area_triangle_three_sides(-1, -2, -1)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle_three_sides() only accepts non-negative values
    >>> area_triangle_three_sides(1, -2, 1)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle_three_sides() only accepts non-negative values
    >>> area_triangle_three_sides(2, 4, 7)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    >>> area_triangle_three_sides(2, 7, 4)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    >>> area_triangle_three_sides(7, 2, 4)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    """
    if side1 < 0 or side2 < 0 or side3 < 0:
        raise ValueError("area_triangle_three_sides() only accepts non-negative values")
    elif side1 + side2 < side3 or side1 + side3 < side2 or side2 + side3 < side1:
        raise ValueError("Given three sides do not form a triangle")
    semi_perimeter = (side1 + side2 + side3) / 2
    area = sqrt(
        semi_perimeter
        * (semi_perimeter - side1)
        * (semi_perimeter - side2)
        * (semi_perimeter - side3)
    )
    return area


def area_parallelogram(base: float, height: float) -> float:
    """
    Calculate the area of a parallelogram.

    >>> area_parallelogram(10, 20)
    200
    >>> area_parallelogram(1.6, 2.6)
    4.16
    >>> area_parallelogram(0, 0)
    0
    >>> area_parallelogram(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    >>> area_parallelogram(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    >>> area_parallelogram(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    """
    if base < 0 or height < 0:
        raise ValueError("area_parallelogram() only accepts non-negative values")
    return base * height


def area_trapezium(base1: float, base2: float, height: float) -> float:
    """
    Calculate the area of a trapezium.

    >>> area_trapezium(10, 20, 30)
    450.0
    >>> area_trapezium(1.6, 2.6, 3.6)
    7.5600000000000005
    >>> area_trapezium(0, 0, 0)
    0.0
    >>> area_trapezium(-1, -2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, -2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    """
    if base1 < 0 or base2 < 0 or height < 0:
        raise ValueError("area_trapezium() only accepts non-negative values")
    return 1 / 2 * (base1 + base2) * height


def area_circle(radius: float) -> float:
    """
    Calculate the area of a circle.

    >>> area_circle(20)
    1256.6370614359173
    >>> area_circle(1.6)
    8.042477193189871
    >>> area_circle(0)
    0.0
    >>> area_circle(-1)
    Traceback (most recent call last):
        ...
    ValueError: area_circle() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("area_circle() only accepts non-negative values")
    return pi * radius**2


def area_ellipse(radius_x: float, radius_y: float) -> float:
    """
    Calculate the area of a ellipse.

    >>> area_ellipse(10, 10)
    314.1592653589793
    >>> area_ellipse(10, 20)
    628.3185307179587
    >>> area_ellipse(0, 0)
    0.0
    >>> area_ellipse(1.6, 2.6)
    13.06902543893354
    >>> area_ellipse(-10, 20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    >>> area_ellipse(10, -20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    >>> area_ellipse(-10, -20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    """
    if radius_x < 0 or radius_y < 0:
        raise ValueError("area_ellipse() only accepts non-negative values")
    return pi * radius_x * radius_y


def area_rhombus(diagonal_1: float, diagonal_2: float) -> float:
    """
    Calculate the area of a rhombus.

    >>> area_rhombus(10, 20)
    100.0
    >>> area_rhombus(1.6, 2.6)
    2.08
    >>> area_rhombus(0, 0)
    0.0
    >>> area_rhombus(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    >>> area_rhombus(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    >>> area_rhombus(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    """
    if diagonal_1 < 0 or diagonal_2 < 0:
        raise ValueError("area_rhombus() only accepts non-negative values")
    return 1 / 2 * diagonal_1 * diagonal_2


def area_reg_polygon(sides: int, length: float) -> float:
    """
    Calculate the area of a regular polygon.
    Wikipedia reference: https://en.wikipedia.org/wiki/Polygon#Regular_polygons
    Formula: (n*s^2*cot(pi/n))/4

    >>> area_reg_polygon(3, 10)
    43.301270189221945
    >>> area_reg_polygon(4, 10)
    100.00000000000001
    >>> area_reg_polygon(0, 0)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    >>> area_reg_polygon(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    >>> area_reg_polygon(5, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts non-negative values as \
length of a side
    >>> area_reg_polygon(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    """
    if not isinstance(sides, int) or sides < 3:
        raise ValueError(
            "area_reg_polygon() only accepts integers greater than or \
equal to three as number of sides"
        )
    elif length < 0:
        raise ValueError(
            "area_reg_polygon() only accepts non-negative values as \
length of a side"
        )
    return (sides * length**2) / (4 * tan(pi / sides))
    return (sides * length**2) / (4 * tan(pi / sides))

def trapezoidal_area(
    fnc: Callable[[float], float],
    x_start: float,
    x_end: float,
    steps: int = 100,
) -> float:
    """
    Treats curve as a collection of linear lines and sums the area of the
    trapezium shape they form
    :param fnc: a function which defines a curve
    :param x_start: left end point to indicate the start of line segment
    :param x_end: right end point to indicate end of line segment
    :param steps: an accuracy gauge; more steps increases the accuracy
    :return: a float representing the length of the curve

    >>> def f(x):
    ...    return 5
    >>> f"{trapezoidal_area(f, 12.0, 14.0, 1000):.3f}"
    '10.000'
    >>> def f(x):
    ...    return 9*x**2
    >>> f"{trapezoidal_area(f, -4.0, 0, 10000):.4f}"
    '192.0000'
    >>> f"{trapezoidal_area(f, -4.0, 4.0, 10000):.4f}"
    '384.0000'
    """
    x1 = x_start
    fx1 = fnc(x_start)
    area = 0.0
    for _ in range(steps):
        # Approximates small segments of curve as linear and solve
        # for trapezoidal area
        x2 = (x_end - x_start) / steps + x1
        fx2 = fnc(x2)
        area += abs(fx2 + fx1) * (x2 - x1) / 2
        # Increment step
        x1 = x2
        fx1 = fx2
    return area

def average_absolute_deviation(nums: list[int]) -> float:
    """
    Return the average absolute deviation of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Average_absolute_deviation

    >>> average_absolute_deviation([0])
    0.0
    >>> average_absolute_deviation([4, 1, 3, 2])
    1.0
    >>> average_absolute_deviation([2, 70, 6, 50, 20, 8, 4, 0])
    20.0
    >>> average_absolute_deviation([-20, 0, 30, 15])
    16.25
    >>> average_absolute_deviation([])
    Traceback (most recent call last):
        ...
    ValueError: List is empty
    """
    if not nums:  # Makes sure that the list is not empty
        raise ValueError("List is empty")

    average = sum(nums) / len(nums)  # Calculate the average
    return sum(abs(x - average) for x in nums) / len(nums)
def mean(nums: list) -> float:
    """
    Find mean of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Mean

    >>> mean([3, 6, 9, 12, 15, 18, 21])
    12.0
    >>> mean([5, 10, 15, 20, 25, 30, 35])
    20.0
    >>> mean([1, 2, 3, 4, 5, 6, 7, 8])
    4.5
    >>> mean([])
    Traceback (most recent call last):
        ...
    ValueError: List is empty
    """
    if not nums:
        raise ValueError("List is empty")
    return sum(nums) / len(nums)
def median(nums: list) -> int | float:
    """
    Find median of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Median

    >>> median([0])
    0
    >>> median([4, 1, 3, 2])
    2.5
    >>> median([2, 70, 6, 50, 20, 8, 4])
    8

    Args:
        nums: List of nums

    Returns:
        Median.
    """
    # The sorted function returns list[SupportsRichComparisonT@sorted]
    # which does not support `+`
    sorted_list: list[int] = sorted(nums)
    length = len(sorted_list)
    mid_index = length >> 1
    return (
        (sorted_list[mid_index] + sorted_list[mid_index - 1]) / 2
        if length % 2 == 0
        else sorted_list[mid_index]
    )

def mode(input_list: list) -> list[Any]:
    """This function returns the mode(Mode as in the measures of
    central tendency) of the input data.

    The input list may contain any Datastructure or any Datatype.

    >>> mode([2, 3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 2, 2, 2])
    [2]
    >>> mode([3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 4, 2, 2, 2])
    [2]
    >>> mode([3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 4, 4, 2, 2, 4, 2])
    [2, 4]
    >>> mode(["x", "y", "y", "z"])
    ['y']
    >>> mode(["x", "x" , "y", "y", "z"])
    ['x', 'y']
    """
    if not input_list:
        return []
    result = [input_list.count(value) for value in input_list]
    y = max(result)  # Gets the maximum count in the input list.
    # Gets values of modes
    return sorted({input_list[i] for i, value in enumerate(result) if value == y})

def bailey_borwein_plouffe(digit_position: int, precision: int = 1000) -> str:
    """
    Implement a popular pi-digit-extraction algorithm known as the
    Bailey-Borwein-Plouffe (BBP) formula to calculate the nth hex digit of pi.
    Wikipedia page:
    https://en.wikipedia.org/wiki/Bailey%E2%80%93Borwein%E2%80%93Plouffe_formula
    @param digit_position: a positive integer representing the position of the digit to
    extract.
    The digit immediately after the decimal point is located at position 1.
    @param precision: number of terms in the second summation to calculate.
    A higher number reduces the chance of an error but increases the runtime.
    @return: a hexadecimal digit representing the digit at the nth position
    in pi's decimal expansion.

    >>> "".join(bailey_borwein_plouffe(i) for i in range(1, 11))
    '243f6a8885'
    >>> bailey_borwein_plouffe(5, 10000)
    '6'
    >>> bailey_borwein_plouffe(-10)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(0)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(1.7)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(2, -10)
    Traceback (most recent call last):
      ...
    ValueError: Precision must be a nonnegative integer
    >>> bailey_borwein_plouffe(2, 1.6)
    Traceback (most recent call last):
      ...
    ValueError: Precision must be a nonnegative integer
    """
    if (not isinstance(digit_position, int)) or (digit_position <= 0):
        raise ValueError("Digit position must be a positive integer")
    elif (not isinstance(precision, int)) or (precision < 0):
        raise ValueError("Precision must be a nonnegative integer")

    # compute an approximation of (16 ** (n - 1)) * pi whose fractional part is mostly
    # accurate
    sum_result = (
        4 * _subsum(digit_position, 1, precision)
        - 2 * _subsum(digit_position, 4, precision)
        - _subsum(digit_position, 5, precision)
        - _subsum(digit_position, 6, precision)
    )

    # return the first hex digit of the fractional part of the result
    return hex(int((sum_result % 1) * 16))[2:]


def _subsum(
    digit_pos_to_extract: int, denominator_addend: int, precision: int
) -> float:
    # only care about first digit of fractional part; don't need decimal
    """
    Private helper function to implement the summation
    functionality.
    @param digit_pos_to_extract: digit position to extract
    @param denominator_addend: added to denominator of fractions in the formula
    @param precision: same as precision in main function
    @return: floating-point number whose integer part is not important
    """
    total = 0.0
    for sum_index in range(digit_pos_to_extract + precision):
        denominator = 8 * sum_index + denominator_addend
        if sum_index < digit_pos_to_extract:
            # if the exponential term is an integer and we mod it by the denominator
            # before dividing, only the integer part of the sum will change;
            # the fractional part will not
            exponential_term = pow(
                16, digit_pos_to_extract - 1 - sum_index, denominator
            )
        else:
            exponential_term = pow(16, digit_pos_to_extract - 1 - sum_index)
        total += exponential_term / denominator
    return total


def decimal_to_negative_base_2(num: int) -> int:
    """
    This function returns the number negative base 2
        of the decimal number of the input data.

    Args:
        int: The decimal number to convert.

    Returns:
        int: The negative base 2 number.

    Examples:
        >>> decimal_to_negative_base_2(0)
        0
        >>> decimal_to_negative_base_2(-19)
        111101
        >>> decimal_to_negative_base_2(4)
        100
        >>> decimal_to_negative_base_2(7)
        11011
    """
    if num == 0:
        return 0
    ans = ""
    while num != 0:
        num, rem = divmod(num, -2)
        if rem < 0:
            rem += 2
            num += 1
        ans = str(rem) + ans
    return int(ans)
def prime_factors(n: int) -> list:
    """Find Prime Factors.
    >>> prime_factors(100)
    [2, 2, 5, 5]
    >>> prime_factors(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive integers have prime factors
    >>> prime_factors(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive integers have prime factors
    """
    if n <= 0:
        raise ValueError("Only positive integers have prime factors")
    pf = []
    while n % 2 == 0:
        pf.append(2)
        n = int(n / 2)
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        while n % i == 0:
            pf.append(i)
            n = int(n / i)
    if n > 2:
        pf.append(n)
    return pf


def number_of_divisors(n: int) -> int:
    """Calculate Number of Divisors of an Integer.
    >>> number_of_divisors(100)
    9
    >>> number_of_divisors(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    >>> number_of_divisors(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    """
    if n <= 0:
        raise ValueError("Only positive numbers are accepted")
    div = 1
    temp = 1
    while n % 2 == 0:
        temp += 1
        n = int(n / 2)
    div *= temp
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        temp = 1
        while n % i == 0:
            temp += 1
            n = int(n / i)
        div *= temp
    if n > 1:
        div *= 2
    return div


def sum_of_divisors(n: int) -> int:
    """Calculate Sum of Divisors.
    >>> sum_of_divisors(100)
    217
    >>> sum_of_divisors(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    >>> sum_of_divisors(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    """
    if n <= 0:
        raise ValueError("Only positive numbers are accepted")
    s = 1
    temp = 1
    while n % 2 == 0:
        temp += 1
        n = int(n / 2)
    if temp > 1:
        s *= (2**temp - 1) / (2 - 1)
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        temp = 1
        while n % i == 0:
            temp += 1
            n = int(n / i)
        if temp > 1:
            s *= (i**temp - 1) / (i - 1)
    return int(s)


def euler_phi(n: int) -> int:
    """Calculate Euler's Phi Function.
    >>> euler_phi(100)
    40
    >>> euler_phi(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    >>> euler_phi(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    """
    if n <= 0:
        raise ValueError("Only positive numbers are accepted")
    s = n
    for x in set(prime_factors(n)):
        s *= (x - 1) / x
    return int(s)
def binary_exp_recursive(base: float, exponent: int) -> float:
    """
    Computes a^b recursively, where a is the base and b is the exponent

    >>> binary_exp_recursive(3, 5)
    243
    >>> binary_exp_recursive(11, 13)
    34522712143931
    >>> binary_exp_recursive(-1, 3)
    -1
    >>> binary_exp_recursive(0, 5)
    0
    >>> binary_exp_recursive(3, 1)
    3
    >>> binary_exp_recursive(3, 0)
    1
    >>> binary_exp_recursive(1.5, 4)
    5.0625
    >>> binary_exp_recursive(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return binary_exp_recursive(base, exponent - 1) * base

    b = binary_exp_recursive(base, exponent // 2)
    return b * b


def binary_exp_iterative(base: float, exponent: int) -> float:
    """
    Computes a^b iteratively, where a is the base and b is the exponent

    >>> binary_exp_iterative(3, 5)
    243
    >>> binary_exp_iterative(11, 13)
    34522712143931
    >>> binary_exp_iterative(-1, 3)
    -1
    >>> binary_exp_iterative(0, 5)
    0
    >>> binary_exp_iterative(3, 1)
    3
    >>> binary_exp_iterative(3, 0)
    1
    >>> binary_exp_iterative(1.5, 4)
    5.0625
    >>> binary_exp_iterative(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res *= base

        base *= base
        exponent >>= 1

    return res


def binary_exp_mod_recursive(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c recursively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_recursive(3, 4, 5)
    1
    >>> binary_exp_mod_recursive(11, 13, 7)
    4
    >>> binary_exp_mod_recursive(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_recursive(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_recursive(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return (binary_exp_mod_recursive(base, exponent - 1, modulus) * base) % modulus

    r = binary_exp_mod_recursive(base, exponent // 2, modulus)
    return (r * r) % modulus


def binary_exp_mod_iterative(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c iteratively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_iterative(3, 4, 5)
    1
    >>> binary_exp_mod_iterative(11, 13, 7)
    4
    >>> binary_exp_mod_iterative(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_iterative(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_iterative(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res = ((res % modulus) * (base % modulus)) % modulus

        base *= base
        exponent >>= 1

    return res

def binary_multiply(a: int, b: int) -> int:
    """
    Multiply 'a' and 'b' using bitwise multiplication.

    Parameters:
    a (int): The first number.
    b (int): The second number.

    Returns:
    int: a * b

    Examples:
    >>> binary_multiply(2, 3)
    6
    >>> binary_multiply(5, 0)
    0
    >>> binary_multiply(3, 4)
    12
    >>> binary_multiply(10, 5)
    50
    >>> binary_multiply(0, 5)
    0
    >>> binary_multiply(2, 1)
    2
    >>> binary_multiply(1, 10)
    10
    """
    res = 0
    while b > 0:
        if b & 1:
            res += a

        a += a
        b >>= 1

    return res


def binary_mod_multiply(a: int, b: int, modulus: int) -> int:
    """
    Calculate (a * b) % c using binary multiplication and modular arithmetic.

    Parameters:
    a (int): The first number.
    b (int): The second number.
    modulus (int): The modulus.

    Returns:
    int: (a * b) % modulus.

    Examples:
    >>> binary_mod_multiply(2, 3, 5)
    1
    >>> binary_mod_multiply(5, 0, 7)
    0
    >>> binary_mod_multiply(3, 4, 6)
    0
    >>> binary_mod_multiply(10, 5, 13)
    11
    >>> binary_mod_multiply(2, 1, 5)
    2
    >>> binary_mod_multiply(1, 10, 3)
    1
    """
    res = 0
    while b > 0:
        if b & 1:
            res = ((res % modulus) + (a % modulus)) % modulus

        a += a
        b >>= 1

    return res
def binomial_coefficient(n: int, r: int) -> int:

    if n < 0 or r < 0:
        raise ValueError("n and r must be non-negative integers")
    if 0 in (n, r):
        return 1
    c = [0 for i in range(r + 1)]
    # nc0 = 1
    c[0] = 1
    for i in range(1, n + 1):
        # to compute current row from previous row.
        j = min(i, r)
        while j > 0:
            c[j] += c[j - 1]
            j -= 1
    return c[r]




def check_polygon(nums: list[float]) -> bool:
    """
    Takes list of possible side lengths and determines whether a
    two-dimensional polygon with such side lengths can exist.

    Returns a boolean value for the < comparison
    of the largest side length with sum of the rest.
    Wiki: https://en.wikipedia.org/wiki/Triangle_inequality

    >>> check_polygon([6, 10, 5])
    True
    >>> check_polygon([3, 7, 13, 2])
    False
    >>> check_polygon([1, 4.3, 5.2, 12.2])
    False
    >>> nums = [3, 7, 13, 2]
    >>> _ = check_polygon(nums) #   Run function, do not show answer in output
    >>> nums #  Check numbers are not reordered
    [3, 7, 13, 2]
    >>> check_polygon([])
    Traceback (most recent call last):
        ...
    ValueError: Monogons and Digons are not polygons in the Euclidean space
    >>> check_polygon([-2, 5, 6])
    Traceback (most recent call last):
        ...
    ValueError: All values must be greater than 0
    """
    if len(nums) < 2:
        raise ValueError("Monogons and Digons are not polygons in the Euclidean space")
    if any(i <= 0 for i in nums):
        raise ValueError("All values must be greater than 0")
    copy_nums = nums.copy()
    copy_nums.sort()
    return copy_nums[-1] < sum(copy_nums[:-1])

def extended_euclid(a: int, b: int) -> tuple[int, int]:
    """
    >>> extended_euclid(10, 6)
    (-1, 2)

    >>> extended_euclid(7, 5)
    (-2, 3)

    """
    if b == 0:
        return (1, 0)
    (x, y) = extended_euclid(b, a % b)
    k = a // b
    return (y, x - k * y)


# Uses ExtendedEuclid to find inverses
def chinese_remainder_theorem(n1: int, r1: int, n2: int, r2: int) -> int:
    """
    >>> chinese_remainder_theorem(5,1,7,3)
    31

    Explanation : 31 is the smallest number such that
                (i)  When we divide it by 5, we get remainder 1
                (ii) When we divide it by 7, we get remainder 3

    >>> chinese_remainder_theorem(6,1,4,3)
    14

    """
    (x, y) = extended_euclid(n1, n2)
    m = n1 * n2
    n = r2 * x * n1 + r1 * y * n2
    return (n % m + m) % m


# ----------SAME SOLUTION USING InvertModulo instead ExtendedEuclid----------------


# This function find the inverses of a i.e., a^(-1)
def invert_modulo(a: int, n: int) -> int:
    """
    >>> invert_modulo(2, 5)
    3

    >>> invert_modulo(8,7)
    1

    """
    (b, x) = extended_euclid(a, n)
    if b < 0:
        b = (b % n + n) % n
    return b


# Same a above using InvertingModulo
def chinese_remainder_theorem2(n1: int, r1: int, n2: int, r2: int) -> int:
    """
    >>> chinese_remainder_theorem2(5,1,7,3)
    31

    >>> chinese_remainder_theorem2(6,1,4,3)
    14

    """
    x, y = invert_modulo(n1, n2), invert_modulo(n2, n1)
    m = n1 * n2
    n = r2 * x * n1 + r1 * y * n2
    return (n % m + m) % m

def pi(precision: int) -> str:
    """
    The Chudnovsky algorithm is a fast method for calculating the digits of PI,
    based on Ramanujan’s PI formulae.

    https://en.wikipedia.org/wiki/Chudnovsky_algorithm

    PI = constant_term / ((multinomial_term * linear_term) / exponential_term)
        where constant_term = 426880 * sqrt(10005)

    The linear_term and the exponential_term can be defined iteratively as follows:
        L_k+1 = L_k + 545140134            where L_0 = 13591409
        X_k+1 = X_k * -262537412640768000  where X_0 = 1

    The multinomial_term is defined as follows:
        6k! / ((3k)! * (k!) ^ 3)
            where k is the k_th iteration.

    This algorithm correctly calculates around 14 digits of PI per iteration

    >>> pi(10)
    '3.14159265'
    >>> pi(100)
    '3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706'
    >>> pi('hello')
    Traceback (most recent call last):
        ...
    TypeError: Undefined for non-integers
    >>> pi(-1)
    Traceback (most recent call last):
        ...
    ValueError: Undefined for non-natural numbers
    """

    if not isinstance(precision, int):
        raise TypeError("Undefined for non-integers")
    elif precision < 1:
        raise ValueError("Undefined for non-natural numbers")

    getcontext().prec = precision
    num_iterations = ceil(precision / 14)
    constant_term = 426880 * Decimal(10005).sqrt()
    exponential_term = 1
    linear_term = 13591409
    partial_sum = Decimal(linear_term)
    for k in range(1, num_iterations):
        multinomial_term = factorial(6 * k) // (factorial(3 * k) * factorial(k) ** 3)
        linear_term += 545140134
        exponential_term *= -262537412640768000
        partial_sum += Decimal(multinomial_term * linear_term) / exponential_term
    return str(constant_term / partial_sum)[:-1]

def collatz_sequence(n: int) -> Generator[int, None, None]:
    """
    Generate the Collatz sequence starting at n.
    >>> tuple(collatz_sequence(2.1))
    Traceback (most recent call last):
        ...
    Exception: Sequence only defined for positive integers
    >>> tuple(collatz_sequence(0))
    Traceback (most recent call last):
        ...
    Exception: Sequence only defined for positive integers
    >>> tuple(collatz_sequence(4))
    (4, 2, 1)
    >>> tuple(collatz_sequence(11))
    (11, 34, 17, 52, 26, 13, 40, 20, 10, 5, 16, 8, 4, 2, 1)
    >>> tuple(collatz_sequence(31))     # doctest: +NORMALIZE_WHITESPACE
    (31, 94, 47, 142, 71, 214, 107, 322, 161, 484, 242, 121, 364, 182, 91, 274, 137,
    412, 206, 103, 310, 155, 466, 233, 700, 350, 175, 526, 263, 790, 395, 1186, 593,
    1780, 890, 445, 1336, 668, 334, 167, 502, 251, 754, 377, 1132, 566, 283, 850, 425,
    1276, 638, 319, 958, 479, 1438, 719, 2158, 1079, 3238, 1619, 4858, 2429, 7288, 3644,
    1822, 911, 2734, 1367, 4102, 2051, 6154, 3077, 9232, 4616, 2308, 1154, 577, 1732,
    866, 433, 1300, 650, 325, 976, 488, 244, 122, 61, 184, 92, 46, 23, 70, 35, 106, 53,
    160, 80, 40, 20, 10, 5, 16, 8, 4, 2, 1)
    >>> tuple(collatz_sequence(43))     # doctest: +NORMALIZE_WHITESPACE
    (43, 130, 65, 196, 98, 49, 148, 74, 37, 112, 56, 28, 14, 7, 22, 11, 34, 17, 52, 26,
    13, 40, 20, 10, 5, 16, 8, 4, 2, 1)
    """
    if not isinstance(n, int) or n < 1:
        raise Exception("Sequence only defined for positive integers")

    yield n
    while n != 1:
        if n % 2 == 0:
            n //= 2
        else:
            n = 3 * n + 1
        yield n

def combinations(n: int, k: int) -> int:
    """
    Returns the number of different combinations of k length which can
    be made from n values, where n >= k.

    Examples:
    >>> combinations(10,5)
    252

    >>> combinations(6,3)
    20

    >>> combinations(20,5)
    15504

    >>> combinations(52, 5)
    2598960

    >>> combinations(0, 0)
    1

    >>> combinations(-4, -5)
    ...
    Traceback (most recent call last):
    ValueError: Please enter positive integers for n and k where n >= k
    """

    # If either of the conditions are true, the function is being asked
    # to calculate a factorial of a negative number, which is not possible
    if n < k or k < 0:
        raise ValueError("Please enter positive integers for n and k where n >= k")
    res = 1
    for i in range(k):
        res *= n - i
        res //= i + 1
    return res

def continued_fraction(num: Fraction) -> list[int]:
    """
    :param num:
    Fraction of the number whose continued fractions to be found.
    Use Fraction(str(number)) for more accurate results due to
    float inaccuracies.

    :return:
    The continued fraction of rational number.
    It is the all commas in the (n + 1)-tuple notation.

    >>> continued_fraction(Fraction(2))
    [2]
    >>> continued_fraction(Fraction("3.245"))
    [3, 4, 12, 4]
    >>> continued_fraction(Fraction("2.25"))
    [2, 4]
    >>> continued_fraction(1/Fraction("2.25"))
    [0, 2, 4]
    >>> continued_fraction(Fraction("415/93"))
    [4, 2, 6, 7]
    >>> continued_fraction(Fraction(0))
    [0]
    >>> continued_fraction(Fraction(0.75))
    [0, 1, 3]
    >>> continued_fraction(Fraction("-2.25"))    # -2.25 = -3 + 0.75
    [-3, 1, 3]
    """
    numerator, denominator = num.as_integer_ratio()
    continued_fraction_list: list[int] = []
    while True:
        integer_part = floor(numerator / denominator)
        continued_fraction_list.append(integer_part)
        numerator -= integer_part * denominator
        if numerator == 0:
            break
        numerator, denominator = denominator, numerator

    return continued_fraction_list
def decimal_isolate(number: float, digit_amount: int) -> float:
    """
    Isolates the decimal part of a number.
    If digitAmount > 0 round to that decimal place, else print the entire decimal.
    >>> decimal_isolate(1.53, 0)
    0.53
    >>> decimal_isolate(35.345, 1)
    0.3
    >>> decimal_isolate(35.345, 2)
    0.34
    >>> decimal_isolate(35.345, 3)
    0.345
    >>> decimal_isolate(-14.789, 3)
    -0.789
    >>> decimal_isolate(0, 2)
    0
    >>> decimal_isolate(-14.123, 1)
    -0.1
    >>> decimal_isolate(-14.123, 2)
    -0.12
    >>> decimal_isolate(-14.123, 3)
    -0.123
    """
    if digit_amount > 0:
        return round(number - int(number), digit_amount)
    return number - int(number)

def decimal_to_fraction(decimal: float | str) -> tuple[int, int]:
    """
    Return a decimal number in its simplest fraction form
    >>> decimal_to_fraction(2)
    (2, 1)
    >>> decimal_to_fraction(89.)
    (89, 1)
    >>> decimal_to_fraction("67")
    (67, 1)
    >>> decimal_to_fraction("45.0")
    (45, 1)
    >>> decimal_to_fraction(1.5)
    (3, 2)
    >>> decimal_to_fraction("6.25")
    (25, 4)
    >>> decimal_to_fraction("78td")
    Traceback (most recent call last):
    ValueError: Please enter a valid number
    """
    try:
        decimal = float(decimal)
    except ValueError:
        raise ValueError("Please enter a valid number")
    fractional_part = decimal - int(decimal)
    if fractional_part == 0:
        return int(decimal), 1
    else:
        number_of_frac_digits = len(str(decimal).split(".")[1])
        numerator = int(decimal * (10**number_of_frac_digits))
        denominator = 10**number_of_frac_digits
        divisor, dividend = denominator, numerator
        while True:
            remainder = dividend % divisor
            if remainder == 0:
                break
            dividend, divisor = divisor, remainder
        numerator, denominator = numerator / divisor, denominator / divisor
        return int(numerator), int(denominator)

def dodecahedron_surface_area(edge: float) -> float:
    """
    Calculates the surface area of a regular dodecahedron
    a = 3 * ((25 + 10 * (5** (1 / 2))) ** (1 / 2 )) * (e**2)
    where:
    a --> is the area of the dodecahedron
    e --> is the length of the edge
    reference-->"Dodecahedron" Study.com
    <https://study.com/academy/lesson/dodecahedron-volume-surface-area-formulas.html>

    :param edge: length of the edge of the dodecahedron
    :type edge: float
    :return: the surface area of the dodecahedron as a float


    Tests:
    >>> dodecahedron_surface_area(5)
    516.1432201766901
    >>> dodecahedron_surface_area(10)
    2064.5728807067603
    >>> dodecahedron_surface_area(-1)
    Traceback (most recent call last):
      ...
    ValueError: Length must be a positive.
    """

    if edge <= 0 or not isinstance(edge, int):
        raise ValueError("Length must be a positive.")
    return 3 * ((25 + 10 * (5 ** (1 / 2))) ** (1 / 2)) * (edge**2)


def dodecahedron_volume(edge: float) -> float:
    """
    Calculates the volume of a regular dodecahedron
    v = ((15 + (7 * (5** (1 / 2)))) / 4) * (e**3)
    where:
    v --> is the volume of the dodecahedron
    e --> is the length of the edge
    reference-->"Dodecahedron" Study.com
    <https://study.com/academy/lesson/dodecahedron-volume-surface-area-formulas.html>

    :param edge: length of the edge of the dodecahedron
    :type edge: float
    :return: the volume of the dodecahedron as a float

    Tests:
    >>> dodecahedron_volume(5)
    957.8898700780791
    >>> dodecahedron_volume(10)
    7663.118960624633
    >>> dodecahedron_volume(-1)
    Traceback (most recent call last):
      ...
    ValueError: Length must be a positive.
    """

    if edge <= 0 or not isinstance(edge, int):
        raise ValueError("Length must be a positive.")
    return ((15 + (7 * (5 ** (1 / 2)))) / 4) * (edge**3)

def double_factorial_recursive(n: int) -> int:
    """
    Compute double factorial using recursive method.
    Recursion can be costly for large numbers.

    To learn about the theory behind this algorithm:
    https://en.wikipedia.org/wiki/Double_factorial

    >>> from math import prod
    >>> all(double_factorial_recursive(i) == prod(range(i, 0, -2)) for i in range(20))
    True
    >>> double_factorial_recursive(0.1)
    Traceback (most recent call last):
        ...
    ValueError: double_factorial_recursive() only accepts integral values
    >>> double_factorial_recursive(-1)
    Traceback (most recent call last):
        ...
    ValueError: double_factorial_recursive() not defined for negative values
    """
    if not isinstance(n, int):
        raise ValueError("double_factorial_recursive() only accepts integral values")
    if n < 0:
        raise ValueError("double_factorial_recursive() not defined for negative values")
    return 1 if n <= 1 else n * double_factorial_recursive(n - 2)


def double_factorial_iterative(num: int) -> int:
    """
    Compute double factorial using iterative method.

    To learn about the theory behind this algorithm:
    https://en.wikipedia.org/wiki/Double_factorial

    >>> from math import prod
    >>> all(double_factorial_iterative(i) == prod(range(i, 0, -2)) for i in range(20))
    True
    >>> double_factorial_iterative(0.1)
    Traceback (most recent call last):
        ...
    ValueError: double_factorial_iterative() only accepts integral values
    >>> double_factorial_iterative(-1)
    Traceback (most recent call last):
        ...
    ValueError: double_factorial_iterative() not defined for negative values
    """
    if not isinstance(num, int):
        raise ValueError("double_factorial_iterative() only accepts integral values")
    if num < 0:
        raise ValueError("double_factorial_iterative() not defined for negative values")
    value = 1
    for i in range(num, 0, -2):
        value *= i
    return value

class Dual:
    def __init__(self, real, rank):
        self.real = real
        if isinstance(rank, int):
            self.duals = [1] * rank
        else:
            self.duals = rank

    def __repr__(self):
        return (
            f"{self.real}+"
            f"{'+'.join(str(dual)+'E'+str(n+1)for n,dual in enumerate(self.duals))}"
        )

    def reduce(self):
        cur = self.duals.copy()
        while cur[-1] == 0:
            cur.pop(-1)
        return Dual(self.real, cur)

    def __add__(self, other):
        if not isinstance(other, Dual):
            return Dual(self.real + other, self.duals)
        s_dual = self.duals.copy()
        o_dual = other.duals.copy()
        if len(s_dual) > len(o_dual):
            o_dual.extend([1] * (len(s_dual) - len(o_dual)))
        elif len(s_dual) < len(o_dual):
            s_dual.extend([1] * (len(o_dual) - len(s_dual)))
        new_duals = []
        for i in range(len(s_dual)):
            new_duals.append(s_dual[i] + o_dual[i])
        return Dual(self.real + other.real, new_duals)

    __radd__ = __add__

    def __sub__(self, other):
        return self + other * -1

    def __mul__(self, other):
        if not isinstance(other, Dual):
            new_duals = []
            for i in self.duals:
                new_duals.append(i * other)
            return Dual(self.real * other, new_duals)
        new_duals = [0] * (len(self.duals) + len(other.duals) + 1)
        for i, item in enumerate(self.duals):
            for j, jtem in enumerate(other.duals):
                new_duals[i + j + 1] += item * jtem
        for k in range(len(self.duals)):
            new_duals[k] += self.duals[k] * other.real
        for index in range(len(other.duals)):
            new_duals[index] += other.duals[index] * self.real
        return Dual(self.real * other.real, new_duals)

    __rmul__ = __mul__

    def __truediv__(self, other):
        if not isinstance(other, Dual):
            new_duals = []
            for i in self.duals:
                new_duals.append(i / other)
            return Dual(self.real / other, new_duals)
        raise ValueError

    def __floordiv__(self, other):
        if not isinstance(other, Dual):
            new_duals = []
            for i in self.duals:
                new_duals.append(i // other)
            return Dual(self.real // other, new_duals)
        raise ValueError

    def __pow__(self, n):
        if n < 0 or isinstance(n, float):
            raise ValueError("power must be a positive integer")
        if n == 0:
            return 1
        if n == 1:
            return self
        x = self
        for _ in range(n - 1):
            x *= self
        return x


def differentiate(func, position, order):
    """
    >>> differentiate(lambda x: x**2, 2, 2)
    2
    >>> differentiate(lambda x: x**2 * x**4, 9, 2)
    196830
    >>> differentiate(lambda y: 0.5 * (y + 3) ** 6, 3.5, 4)
    7605.0
    >>> differentiate(lambda y: y ** 2, 4, 3)
    0
    >>> differentiate(8, 8, 8)
    Traceback (most recent call last):
        ...
    ValueError: differentiate() requires a function as input for func
    >>> differentiate(lambda x: x **2, "", 1)
    Traceback (most recent call last):
        ...
    ValueError: differentiate() requires a float as input for position
    >>> differentiate(lambda x: x**2, 3, "")
    Traceback (most recent call last):
        ...
    ValueError: differentiate() requires an int as input for order
    """
    if not callable(func):
        raise ValueError("differentiate() requires a function as input for func")
    if not isinstance(position, (float, int)):
        raise ValueError("differentiate() requires a float as input for position")
    if not isinstance(order, int):
        raise ValueError("differentiate() requires an int as input for order")
    d = Dual(position, 1)
    result = func(d)
    if order == 0:
        return result.real
    return result.duals[order - 1] * factorial(order)

def calculate_prob(text: str) -> None:
    """
    This method takes path and two dict as argument
    and than calculates entropy of them.
    :param dict:
    :param dict:
    :return: Prints
    1) Entropy of information based on 1 alphabet
    2) Entropy of information based on couples of 2 alphabet
    3) print Entropy of H(X n∣Xn−1)

    Text from random books. Also, random quotes.
    >>> text = ("Behind Winston’s back the voice "
    ...         "from the telescreen was still "
    ...         "babbling and the overfulfilment")
    >>> calculate_prob(text)
    4.0
    6.0
    2.0

    >>> text = ("The Ministry of Truth—Minitrue, in Newspeak [Newspeak was the official"
    ...         "face in elegant lettering, the three")
    >>> calculate_prob(text)
    4.0
    5.0
    1.0
    >>> text = ("Had repulsive dashwoods suspicion sincerity but advantage now him. "
    ...         "Remark easily garret nor nay.  Civil those mrs enjoy shy fat merry. "
    ...         "You greatest jointure saw horrible. He private he on be imagine "
    ...         "suppose. Fertile beloved evident through no service elderly is. Blind "
    ...         "there if every no so at. Own neglected you preferred way sincerity "
    ...         "delivered his attempted. To of message cottage windows do besides "
    ...         "against uncivil.  Delightful unreserved impossible few estimating "
    ...         "men favourable see entreaties. She propriety immediate was improving. "
    ...         "He or entrance humoured likewise moderate. Much nor game son say "
    ...         "feel. Fat make met can must form into gate. Me we offending prevailed "
    ...         "discovery.")
    >>> calculate_prob(text)
    4.0
    7.0
    3.0
    """
    single_char_strings, two_char_strings = analyze_text(text)
    my_alphas = list(" " + ascii_lowercase)
    # what is our total sum of probabilities.
    all_sum = sum(single_char_strings.values())

    # one length string
    my_fir_sum = 0
    # for each alpha we go in our dict and if it is in it we calculate entropy
    for ch in my_alphas:
        if ch in single_char_strings:
            my_str = single_char_strings[ch]
            prob = my_str / all_sum
            my_fir_sum += prob * math.log2(prob)  # entropy formula.

    # print entropy
    print(f"{round(-1 * my_fir_sum):.1f}")

    # two len string
    all_sum = sum(two_char_strings.values())
    my_sec_sum = 0
    # for each alpha (two in size) calculate entropy.
    for ch0 in my_alphas:
        for ch1 in my_alphas:
            sequence = ch0 + ch1
            if sequence in two_char_strings:
                my_str = two_char_strings[sequence]
                prob = int(my_str) / all_sum
                my_sec_sum += prob * math.log2(prob)

    # print second entropy
    print(f"{round(-1 * my_sec_sum):.1f}")

    # print the difference between them
    print(f"{round((-1 * my_sec_sum) - (-1 * my_fir_sum)):.1f}")


def analyze_text(text: str) -> tuple[dict, dict]:
    """
    Convert text input into two dicts of counts.
    The first dictionary stores the frequency of single character strings.
    The second dictionary stores the frequency of two character strings.
    """
    single_char_strings = Counter()  # type: ignore
    two_char_strings = Counter()  # type: ignore
    single_char_strings[text[-1]] += 1

    # first case when we have space at start.
    two_char_strings[" " + text[0]] += 1
    for i in range(len(text) - 1):
        single_char_strings[text[i]] += 1
        two_char_strings[text[i : i + 2]] += 1
    return single_char_strings, two_char_strings

def euclidean_distance(vector_1: Vector, vector_2: Vector) -> VectorOut:
    """
    Calculate the distance between the two endpoints of two vectors.
    A vector is defined as a list, tuple, or numpy 1D array.
    >>> euclidean_distance((0, 0), (2, 2))
    2.8284271247461903
    >>> euclidean_distance(np.array([0, 0, 0]), np.array([2, 2, 2]))
    3.4641016151377544
    >>> euclidean_distance(np.array([1, 2, 3, 4]), np.array([5, 6, 7, 8]))
    8.0
    >>> euclidean_distance([1, 2, 3, 4], [5, 6, 7, 8])
    8.0
    """
    return np.sqrt(np.sum((np.asarray(vector_1) - np.asarray(vector_2)) ** 2))


def euclidean_distance_no_np(vector_1: Vector, vector_2: Vector) -> VectorOut:
    """
    Calculate the distance between the two endpoints of two vectors without numpy.
    A vector is defined as a list, tuple, or numpy 1D array.
    >>> euclidean_distance_no_np((0, 0), (2, 2))
    2.8284271247461903
    >>> euclidean_distance_no_np([1, 2, 3, 4], [5, 6, 7, 8])
    8.0
    """
    return sum((v1 - v2) ** 2 for v1, v2 in zip(vector_1, vector_2)) ** (1 / 2)

def explicit_euler(
    ode_func: Callable, y0: float, x0: float, step_size: float, x_end: float
) -> np.ndarray:
    """Calculate numeric solution at each step to an ODE using Euler's Method

    For reference to Euler's method refer to https://en.wikipedia.org/wiki/Euler_method.

    Args:
        ode_func (Callable):  The ordinary differential equation
            as a function of x and y.
        y0 (float): The initial value for y.
        x0 (float): The initial value for x.
        step_size (float): The increment value for x.
        x_end (float): The final value of x to be calculated.

    Returns:
        np.ndarray: Solution of y for every step in x.

    >>> # the exact solution is math.exp(x)
    >>> def f(x, y):
    ...     return y
    >>> y0 = 1
    >>> y = explicit_euler(f, y0, 0.0, 0.01, 5)
    >>> y[-1]
    144.77277243257308
    """
    n = int(np.ceil((x_end - x0) / step_size))
    y = np.zeros((n + 1,))
    y[0] = y0
    x = x0

    for k in range(n):
        y[k + 1] = y[k] + step_size * ode_func(x, y[k])
        x += step_size

    return y

def euler_modified(
    ode_func: Callable, y0: float, x0: float, step_size: float, x_end: float
) -> np.ndarray:
    """
    Calculate solution at each step to an ODE using Euler's Modified Method
    The Euler Method is straightforward to implement, but can't give accurate solutions.
    So, some changes were proposed to improve accuracy.

    https://en.wikipedia.org/wiki/Euler_method

    Arguments:
    ode_func -- The ode as a function of x and y
    y0 -- the initial value for y
    x0 -- the initial value for x
    stepsize -- the increment value for x
    x_end -- the end value for x

    >>> # the exact solution is math.exp(x)
    >>> def f1(x, y):
    ...     return -2*x*(y**2)
    >>> y = euler_modified(f1, 1.0, 0.0, 0.2, 1.0)
    >>> y[-1]
    0.503338255442106
    >>> import math
    >>> def f2(x, y):
    ...     return -2*y + (x**3)*math.exp(-2*x)
    >>> y = euler_modified(f2, 1.0, 0.0, 0.1, 0.3)
    >>> y[-1]
    0.5525976431951775
    """
    n = int(np.ceil((x_end - x0) / step_size))
    y = np.zeros((n + 1,))
    y[0] = y0
    x = x0

    for k in range(n):
        y_get = y[k] + step_size * ode_func(x, y[k])
        y[k + 1] = y[k] + (
            (step_size / 2) * (ode_func(x, y[k]) + ode_func(x + step_size, y_get))
        )
        x += step_size

    return y

def totient(n: int) -> list:
    """
    >>> n = 10
    >>> totient_calculation = totient(n)
    >>> for i in range(1, n):
    ...     print(f"{i} has {totient_calculation[i]} relative primes.")
    1 has 0 relative primes.
    2 has 1 relative primes.
    3 has 2 relative primes.
    4 has 2 relative primes.
    5 has 4 relative primes.
    6 has 2 relative primes.
    7 has 6 relative primes.
    8 has 4 relative primes.
    9 has 6 relative primes.
    """
    is_prime = [True for i in range(n + 1)]
    totients = [i - 1 for i in range(n + 1)]
    primes = []
    for i in range(2, n + 1):
        if is_prime[i]:
            primes.append(i)
        for j in range(len(primes)):
            if i * primes[j] >= n:
                break
            is_prime[i * primes[j]] = False

            if i % primes[j] == 0:
                totients[i * primes[j]] = totients[i] * primes[j]
                break

            totients[i * primes[j]] = totients[i] * (primes[j] - 1)

    return totients

def extended_euclidean_algorithm(a: int, b: int) -> tuple[int, int]:
    """
    Extended Euclidean Algorithm.

    Finds 2 numbers a and b such that it satisfies
    the equation am + bn = gcd(m, n) (a.k.a Bezout's Identity)

    >>> extended_euclidean_algorithm(1, 24)
    (1, 0)

    >>> extended_euclidean_algorithm(8, 14)
    (2, -1)

    >>> extended_euclidean_algorithm(240, 46)
    (-9, 47)

    >>> extended_euclidean_algorithm(1, -4)
    (1, 0)

    >>> extended_euclidean_algorithm(-2, -4)
    (-1, 0)

    >>> extended_euclidean_algorithm(0, -4)
    (0, -1)

    >>> extended_euclidean_algorithm(2, 0)
    (1, 0)

    """
    # base cases
    if abs(a) == 1:
        return a, 0
    elif abs(b) == 1:
        return 0, b

    old_remainder, remainder = a, b
    old_coeff_a, coeff_a = 1, 0
    old_coeff_b, coeff_b = 0, 1

    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_coeff_a, coeff_a = coeff_a, old_coeff_a - quotient * coeff_a
        old_coeff_b, coeff_b = coeff_b, old_coeff_b - quotient * coeff_b

    # sign correction for negative numbers
    if a < 0:
        old_coeff_a = -old_coeff_a
    if b < 0:
        old_coeff_b = -old_coeff_b

    return old_coeff_a, old_coeff_b

def factorial(number: int) -> int:
    """
    Calculate the factorial of specified number (n!).

    >>> import math
    >>> all(factorial(i) == math.factorial(i) for i in range(20))
    True
    >>> factorial(0.1)
    Traceback (most recent call last):
        ...
    ValueError: factorial() only accepts integral values
    >>> factorial(-1)
    Traceback (most recent call last):
        ...
    ValueError: factorial() not defined for negative values
    >>> factorial(1)
    1
    >>> factorial(6)
    720
    >>> factorial(0)
    1
    """
    if number != int(number):
        raise ValueError("factorial() only accepts integral values")
    if number < 0:
        raise ValueError("factorial() not defined for negative values")
    value = 1
    for i in range(1, number + 1):
        value *= i
    return value


def factorial_recursive(n: int) -> int:
    """
    Calculate the factorial of a positive integer
    https://en.wikipedia.org/wiki/Factorial

    >>> import math
    >>> all(factorial(i) == math.factorial(i) for i in range(20))
    True
    >>> factorial(0.1)
    Traceback (most recent call last):
        ...
    ValueError: factorial() only accepts integral values
    >>> factorial(-1)
    Traceback (most recent call last):
        ...
    ValueError: factorial() not defined for negative values
    """
    if not isinstance(n, int):
        raise ValueError("factorial() only accepts integral values")
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    return 1 if n in {0, 1} else n * factorial(n - 1)


def factors_of_a_number(num: int) -> list:
    """
    >>> factors_of_a_number(1)
    [1]
    >>> factors_of_a_number(5)
    [1, 5]
    >>> factors_of_a_number(24)
    [1, 2, 3, 4, 6, 8, 12, 24]
    >>> factors_of_a_number(-24)
    []
    """
    facs: list[int] = []
    if num < 1:
        return facs
    facs.append(1)
    if num == 1:
        return facs
    facs.append(num)
    for i in range(2, int(sqrt(num)) + 1):
        if num % i == 0:  # If i is a factor of num
            facs.append(i)
            d = num // i  # num//i is the other factor of num
            if d != i:  # If d and i are distinct
                facs.append(d)  # we have found another factor
    facs.sort()
    return facs

def fast_inverse_sqrt(number: float) -> float:
    """
    Compute the fast inverse square root of a floating-point number using the famous
    Quake III algorithm.

    :param float number: Input number for which to calculate the inverse square root.
    :return float: The fast inverse square root of the input number.

    Example:
    >>> fast_inverse_sqrt(10)
    0.3156857923527257
    >>> fast_inverse_sqrt(4)
    0.49915357479239103
    >>> fast_inverse_sqrt(4.1)
    0.4932849504615651
    >>> fast_inverse_sqrt(0)
    Traceback (most recent call last):
        ...
    ValueError: Input must be a positive number.
    >>> fast_inverse_sqrt(-1)
    Traceback (most recent call last):
        ...
    ValueError: Input must be a positive number.
    >>> from math import isclose, sqrt
    >>> all(isclose(fast_inverse_sqrt(i), 1 / sqrt(i), rel_tol=0.00132)
    ...     for i in range(50, 60))
    True
    """
    if number <= 0:
        raise ValueError("Input must be a positive number.")
    i = struct.unpack(">i", struct.pack(">f", number))[0]
    i = 0x5F3759DF - (i >> 1)
    y = struct.unpack(">f", struct.pack(">i", i))[0]
    return y * (1.5 - 0.5 * number * y * y)


def fib_iterative_yield(n: int) -> Iterator[int]:
    """
    Calculates the first n (1-indexed) Fibonacci numbers using iteration with yield
    >>> list(fib_iterative_yield(0))
    [0]
    >>> tuple(fib_iterative_yield(1))
    (0, 1)
    >>> tuple(fib_iterative_yield(5))
    (0, 1, 1, 2, 3, 5)
    >>> tuple(fib_iterative_yield(10))
    (0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55)
    >>> tuple(fib_iterative_yield(-1))
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    """
    if n < 0:
        raise ValueError("n is negative")
    a, b = 0, 1
    yield a
    for _ in range(n):
        yield b
        a, b = b, a + b


def fib_iterative(n: int) -> list[int]:
    """
    Calculates the first n (0-indexed) Fibonacci numbers using iteration
    >>> fib_iterative(0)
    [0]
    >>> fib_iterative(1)
    [0, 1]
    >>> fib_iterative(5)
    [0, 1, 1, 2, 3, 5]
    >>> fib_iterative(10)
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    >>> fib_iterative(-1)
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    """
    if n < 0:
        raise ValueError("n is negative")
    if n == 0:
        return [0]
    fib = [0, 1]
    for _ in range(n - 1):
        fib.append(fib[-1] + fib[-2])
    return fib


def fib_recursive(n: int) -> list[int]:
    """
    Calculates the first n (0-indexed) Fibonacci numbers using recursion
    >>> fib_iterative(0)
    [0]
    >>> fib_iterative(1)
    [0, 1]
    >>> fib_iterative(5)
    [0, 1, 1, 2, 3, 5]
    >>> fib_iterative(10)
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    >>> fib_iterative(-1)
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    """

    def fib_recursive_term(i: int) -> int:
        """
        Calculates the i-th (0-indexed) Fibonacci number using recursion
        >>> fib_recursive_term(0)
        0
        >>> fib_recursive_term(1)
        1
        >>> fib_recursive_term(5)
        5
        >>> fib_recursive_term(10)
        55
        >>> fib_recursive_term(-1)
        Traceback (most recent call last):
            ...
        Exception: n is negative
        """
        if i < 0:
            raise ValueError("n is negative")
        if i < 2:
            return i
        return fib_recursive_term(i - 1) + fib_recursive_term(i - 2)

    if n < 0:
        raise ValueError("n is negative")
    return [fib_recursive_term(i) for i in range(n + 1)]


def fib_recursive_cached(n: int) -> list[int]:
    """
    Calculates the first n (0-indexed) Fibonacci numbers using recursion
    >>> fib_iterative(0)
    [0]
    >>> fib_iterative(1)
    [0, 1]
    >>> fib_iterative(5)
    [0, 1, 1, 2, 3, 5]
    >>> fib_iterative(10)
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    >>> fib_iterative(-1)
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    """

    @functools.cache
    def fib_recursive_term(i: int) -> int:
        """
        Calculates the i-th (0-indexed) Fibonacci number using recursion
        """
        if i < 0:
            raise ValueError("n is negative")
        if i < 2:
            return i
        return fib_recursive_term(i - 1) + fib_recursive_term(i - 2)

    if n < 0:
        raise ValueError("n is negative")
    return [fib_recursive_term(i) for i in range(n + 1)]


def fib_memoization(n: int) -> list[int]:
    """
    Calculates the first n (0-indexed) Fibonacci numbers using memoization
    >>> fib_memoization(0)
    [0]
    >>> fib_memoization(1)
    [0, 1]
    >>> fib_memoization(5)
    [0, 1, 1, 2, 3, 5]
    >>> fib_memoization(10)
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    >>> fib_iterative(-1)
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    """
    if n < 0:
        raise ValueError("n is negative")
    # Cache must be outside recursuive function
    # other it will reset every time it calls itself.
    cache: dict[int, int] = {0: 0, 1: 1, 2: 1}  # Prefilled cache

    def rec_fn_memoized(num: int) -> int:
        if num in cache:
            return cache[num]

        value = rec_fn_memoized(num - 1) + rec_fn_memoized(num - 2)
        cache[num] = value
        return value

    return [rec_fn_memoized(i) for i in range(n + 1)]


def fib_binet(n: int) -> list[int]:
    """
    Calculates the first n (0-indexed) Fibonacci numbers using a simplified form
    of Binet's formula:
    https://en.m.wikipedia.org/wiki/Fibonacci_number#Computation_by_rounding

    NOTE 1: this function diverges from fib_iterative at around n = 71, likely
    due to compounding floating-point arithmetic errors

    NOTE 2: this function doesn't accept n >= 1475 because it overflows
    thereafter due to the size limitations of Python floats
    >>> fib_binet(0)
    [0]
    >>> fib_binet(1)
    [0, 1]
    >>> fib_binet(5)
    [0, 1, 1, 2, 3, 5]
    >>> fib_binet(10)
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    >>> fib_binet(-1)
    Traceback (most recent call last):
        ...
    ValueError: n is negative
    >>> fib_binet(1475)
    Traceback (most recent call last):
        ...
    ValueError: n is too large
    """
    if n < 0:
        raise ValueError("n is negative")
    if n >= 1475:
        raise ValueError("n is too large")
    sqrt_5 = sqrt(5)
    phi = (1 + sqrt_5) / 2
    return [round(phi**i / sqrt_5) for i in range(n + 1)]

def find_max_iterative(nums: list[int | float]) -> int | float:
    """
    >>> for nums in ([3, 2, 1], [-3, -2, -1], [3, -3, 0], [3.0, 3.1, 2.9]):
    ...     find_max_iterative(nums) == max(nums)
    True
    True
    True
    True
    >>> find_max_iterative([2, 4, 9, 7, 19, 94, 5])
    94
    >>> find_max_iterative([])
    Traceback (most recent call last):
        ...
    ValueError: find_max_iterative() arg is an empty sequence
    """
    if len(nums) == 0:
        raise ValueError("find_max_iterative() arg is an empty sequence")
    max_num = nums[0]
    for x in nums:
        if x > max_num:
            max_num = x
    return max_num


# Divide and Conquer algorithm
def find_max_recursive(nums: list[int | float], left: int, right: int) -> int | float:
    """
    find max value in list
    :param nums: contains elements
    :param left: index of first element
    :param right: index of last element
    :return: max in nums

    >>> for nums in ([3, 2, 1], [-3, -2, -1], [3, -3, 0], [3.0, 3.1, 2.9]):
    ...     find_max_recursive(nums, 0, len(nums) - 1) == max(nums)
    True
    True
    True
    True
    >>> nums = [1, 3, 5, 7, 9, 2, 4, 6, 8, 10]
    >>> find_max_recursive(nums, 0, len(nums) - 1) == max(nums)
    True
    >>> find_max_recursive([], 0, 0)
    Traceback (most recent call last):
        ...
    ValueError: find_max_recursive() arg is an empty sequence
    >>> find_max_recursive(nums, 0, len(nums)) == max(nums)
    Traceback (most recent call last):
        ...
    IndexError: list index out of range
    >>> find_max_recursive(nums, -len(nums), -1) == max(nums)
    True
    >>> find_max_recursive(nums, -len(nums) - 1, -1) == max(nums)
    Traceback (most recent call last):
        ...
    IndexError: list index out of range
    """
    if len(nums) == 0:
        raise ValueError("find_max_recursive() arg is an empty sequence")
    if (
        left >= len(nums)
        or left < -len(nums)
        or right >= len(nums)
        or right < -len(nums)
    ):
        raise IndexError("list index out of range")
    if left == right:
        return nums[left]
    mid = (left + right) >> 1  # the middle
    left_max = find_max_recursive(nums, left, mid)  # find max in range[left, mid]
    right_max = find_max_recursive(
        nums, mid + 1, right
    )  # find max in range[mid + 1, right]

    return left_max if left_max >= right_max else right_max

def find_min_iterative(nums: list[int | float]) -> int | float:
    """
    Find Minimum Number in a List
    :param nums: contains elements
    :return: min number in list

    >>> for nums in ([3, 2, 1], [-3, -2, -1], [3, -3, 0], [3.0, 3.1, 2.9]):
    ...     find_min_iterative(nums) == min(nums)
    True
    True
    True
    True
    >>> find_min_iterative([0, 1, 2, 3, 4, 5, -3, 24, -56])
    -56
    >>> find_min_iterative([])
    Traceback (most recent call last):
        ...
    ValueError: find_min_iterative() arg is an empty sequence
    """
    if len(nums) == 0:
        raise ValueError("find_min_iterative() arg is an empty sequence")
    min_num = nums[0]
    for num in nums:
        min_num = min(min_num, num)
    return min_num


# Divide and Conquer algorithm
def find_min_recursive(nums: list[int | float], left: int, right: int) -> int | float:
    """
    find min value in list
    :param nums: contains elements
    :param left: index of first element
    :param right: index of last element
    :return: min in nums

    >>> for nums in ([3, 2, 1], [-3, -2, -1], [3, -3, 0], [3.0, 3.1, 2.9]):
    ...     find_min_recursive(nums, 0, len(nums) - 1) == min(nums)
    True
    True
    True
    True
    >>> nums = [1, 3, 5, 7, 9, 2, 4, 6, 8, 10]
    >>> find_min_recursive(nums, 0, len(nums) - 1) == min(nums)
    True
    >>> find_min_recursive([], 0, 0)
    Traceback (most recent call last):
        ...
    ValueError: find_min_recursive() arg is an empty sequence
    >>> find_min_recursive(nums, 0, len(nums)) == min(nums)
    Traceback (most recent call last):
        ...
    IndexError: list index out of range
    >>> find_min_recursive(nums, -len(nums), -1) == min(nums)
    True
    >>> find_min_recursive(nums, -len(nums) - 1, -1) == min(nums)
    Traceback (most recent call last):
        ...
    IndexError: list index out of range
    """
    if len(nums) == 0:
        raise ValueError("find_min_recursive() arg is an empty sequence")
    if (
        left >= len(nums)
        or left < -len(nums)
        or right >= len(nums)
        or right < -len(nums)
    ):
        raise IndexError("list index out of range")
    if left == right:
        return nums[left]
    mid = (left + right) >> 1  # the middle
    left_min = find_min_recursive(nums, left, mid)  # find min in range[left, mid]
    right_min = find_min_recursive(
        nums, mid + 1, right
    )  # find min in range[mid + 1, right]

    return left_min if left_min <= right_min else right_min

def floor(x: float) -> int:
    """
    Return the floor of x as an Integral.
    :param x: the number
    :return: the largest integer <= x.
    >>> import math
    >>> all(floor(n) == math.floor(n) for n
    ...     in (1, -1, 0, -0, 1.1, -1.1, 1.0, -1.0, 1_000_000_000))
    True
    """
    return int(x) if x - int(x) >= 0 else int(x) - 1