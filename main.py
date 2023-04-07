import openpyxl
from openpyxl.styles import PatternFill
from dotenv import load_dotenv

from src.immowelt import get_immowelt_results
from src.immoscout import get_immoscout_results

# Load the environment variables from the .env file
load_dotenv()


def _create_workbook():
    # create a new workbook and select the active worksheet
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    # add headers
    worksheet['A1'] = 'Type'
    worksheet['B1'] = 'Title'
    worksheet['C1'] = 'Price'
    worksheet['D1'] = 'Area'
    worksheet['E1'] = 'Ratio'
    worksheet['F1'] = 'Link'

    return workbook


def _get_cell_style(type, value):
    green = '008000'
    yellow = 'FFFF00'
    red = 'FF0000'
    color = 'FFFFF0'
    limits = type.get_limits()
    if value is None:
        return PatternFill(start_color=color, end_color=color, fill_type='solid')
    if value > 0:
        color = green
    if value >= limits[0]:
        color = yellow
    if value > limits[1]:
        color = red

    return PatternFill(start_color=color, end_color=color, fill_type='solid')


def _load_and_store_data():
    workbook = _create_workbook()
    worksheet = workbook.active
    results = get_immowelt_results() + get_immoscout_results()
    results = sorted(results, key=lambda result: (
        result.type.name, result.ratio))

    for row, result in enumerate(results, start=2):
        worksheet.cell(row=row, column=1, value=result.type.name)
        worksheet.cell(row=row, column=2, value=result.title)
        worksheet.cell(row=row, column=3, value=result.price)
        worksheet.cell(row=row, column=4, value=result.area)
        worksheet.cell(row=row, column=5,
                       value=result.ratio).fill = _get_cell_style(result.type, result.ratio)
        worksheet.cell(row=row, column=6, value=result.link)

    workbook.save('immo-results.xlsx')


# Load and store data in .xls file
_load_and_store_data()
