import datetime
from dateutil.relativedelta import relativedelta

def sanitize_inputs(value: str):
    cleaned_input = value.strip("<@!>")

    if cleaned_input.isdigit():
        return int(cleaned_input)
    return cleaned_input


def str_to_time(value: str) -> datetime.datetime | bool:
    str_time, unit = value[:-1], value[-1:]

    if not str_time.isdigit():
        return False
    
    current_time = datetime.datetime.now(datetime.timezone.utc)
    time = int(str_time)
    match unit:
        case "m":
            return current_time + relativedelta(minutes=time)
        case "h":
            return current_time + relativedelta(hours=time)
        case "d":
            return current_time + relativedelta(days=time)
        case "w":
            return current_time + relativedelta(weeks=time)
        case "y":
            return current_time + relativedelta(years=time)
        case _:
            return False
        
def date_to_time(date: str) -> str:
    match date[-1:]:
        case "m":
            preffix = "minutes"
        case "h":
            preffix = "hours"
        case "d":
            preffix = "days"
        case "w":
            preffix = "weeks"
        case "y":
            preffix = "years"
        case _:
            preffix = ""

    return f"{date[:-1]} {preffix}"


def time_between_dates(dt1: datetime.datetime, dt2: datetime.datetime):
    start, end = min(dt1, dt2), max(dt1, dt2)
    
    diff = relativedelta(end, start)
    

    units = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
    parts = []
    
    for unit in units:
        value = getattr(diff, unit)
        if value:
            unit_name = unit[:-1] if value == 1 else unit
            parts.append(f"{value} {unit_name}")
            
    return ", ".join(parts) if parts else "0 seconds"