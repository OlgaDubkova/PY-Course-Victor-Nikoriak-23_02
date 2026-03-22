def func(name):
    def in_func():
        return f'Hi {name}!'
    return in_func

call_func = func('Katty')
print(call_func())