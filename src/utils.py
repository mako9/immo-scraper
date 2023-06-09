import re

def get_int_value_from_string(input_string):
    if input_string is None:
        return None
    try:
        numbers = re.findall(r'\d+', input_string.replace('.', '').replace(',', '.'))
        if len(numbers) > 0:
            return float(numbers[0])
        else:
            return -1
    except TypeError as e:
        print(e)