- for strings wrap in "" or '' is the same thing

- float is decimal numbers

- when typing string, at the end can use end = \n to go to new line

- input is always a string unless converted, to store the input, assign it to a variable

- == means compare, = means assign

- if else statements need a colon after if and after else

- functions are defined with def, and called by writing the name with parentheses

- return sends a value back from a function

- cases can be done with match statement:

    name = input("what is your name: ")

    match name:
        case "hk":
        print("baller")
        case "mk":
            print("baller")
        case "lk":
            print("baller")
        case "abdoon":
            print("bangerrrr")
        case _:
            print("Who?")


- list is in sqaure brackets [], can store different types

    - lists are mutable (can be changed), strings are immutable (cannot be changed), so if I do x[0] = "a" but x at 0 was "b" before, it will change to "a"
    - len gives length of list, also works in strings (index in list starts at 0)
    - x.append adds to end of list
    - x.insert(index, value) adds value at index
    - x.extend(another_list) adds all values from another list to x
    - x.pop(index) removes value at index, printing it will show the removed value and then remove it from the list
    - x.remove(value) removes first occurrence of value in list

- tuples are in parentheses ()

    - cannot append, remove, or change values in tuple

- a slice is part of a list or string, x[start:stop:step] gets values from start to stop-1 with step, it doesn't include the stop index value
- when leaving blank, ex. x[:3] gets from beginning to index 2, and x[3:] gets from index 3 to the end, x[::-1] reverses the list or string

- for loops need a colon after the for statement

    - for i in range(n): means repeat n times
    - start, stop, step can be used in range like range(1, 10, 2)
    - can also use for loop in a list, remember square brackets inside the for i in list([])

- sets are in curly braces {}, sets cannot have duplicate values
- x.set() creates an empty set
- if s = {1,3,4,2}, it creates a dictionary with keys 1,3,4,2 and values None
- can add to set with s.add(value) and remove with s.remove(value)
- can union sets with print(s.union(s2))
- can do difference with print(s.difference(s2))
- can do intersection with print(s.intersection(s2))

- dictionaries are in curly braces {}, they store key:value pairs
- format is d = {key1: value1, key2: value2} and they have values that you can assign them to
- can add to dictionary with d[key] = value
- can check if key in dictionary with print(key in d)
- can get all values from dictionary with print(d.values())
- delete key:value pair with del d[key]

- comprehensions can create lists, sets, or dictionaries in a single line of code
- example: x = [[0 for x in range(3)] for x in range(3)] creates a 3x3 list of lists with all 0s

- to define a function: def function_name(parameters):
- the arguments: function_name(arg1, arg2)
- can separate multiple variables for the function
    example:
          def func(x,y,z=None):
          print("run', x,y)

          r1, r2 = func(1, 2)
          print(r1, r2)

- print(*x) unpacks the list x and prints each value separated by space with the brackets
- *args allows for variable number of arguments in a function

- raise Exception("message") raises an exception with the given message

- to handle exceptions, use try and except blocks, as well as finally block

    try:
        x = 7 / 0

    except Exception as e:
        print("Error:", e)

    finally:
        print("This runs no matter what")

 - Lambda example:
 
        x = lambda x, y: x + y
        print(x(2, 3))

- map example:

    x = [1, 2, 3, 4, 5]
    mp = map(lambda i: i * 2, x)
    print(list(mp))

- F strings example:
    name = "hk"
    age = 20
    print(f"My name is {name} and I am {age} years old.")