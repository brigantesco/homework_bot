class SalaryNotInRangeError(Exception):
    """Исключение возникает из-за ошибок в зарплате.

    Атрибуты:
        salary: входная зарплата, вызвавшая ошибку
        message: объяснение ошибки
    """

    def __init__(self, salary, message):
        self.salary = salary
        self.message = message
        # переопределяется конструктор встроенного класса `Exception()`
        super().__init__(self.message)


salary = int(input("Введите сумму зарплаты: "))
if not 5000 < salary < 15000:
    raise SalaryNotInRangeError(salary)1