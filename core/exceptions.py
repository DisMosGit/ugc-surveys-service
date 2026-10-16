class DomainError(Exception):
    status_code = 400
    default_detail = "Некорректный запрос"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class EntityInUse(DomainError):
    status_code = 409
    default_detail = "Объект уже используется и не может быть удалён"


class InvalidOrdering(DomainError):
    default_detail = "Порядок должен содержать все элементы без пропусков и повторов"


class SessionCompleted(DomainError):
    status_code = 409
    default_detail = "Прохождение уже завершено"


class OptionsNotAllowed(DomainError):
    default_detail = "Для вопроса со свободным ответом варианты ответа не предусмотрены"
