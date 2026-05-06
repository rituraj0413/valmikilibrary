from datetime import date
from decimal import Decimal
from urllib.parse import quote

from .models import Payment


MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def month_label(year, month):
    return date(year, month, 1).strftime('%B %Y')


def paid_lookup(student, year=None):
    payments = Payment.objects.filter(student=student, is_paid=True)
    if year is not None:
        payments = payments.filter(year=year)
    return {(payment.year, payment.month): payment for payment in payments}


def get_month_status(student, year, month, today, payments=None):
    payments = payments if payments is not None else paid_lookup(student, year)
    payment = payments.get((year, month))
    joining_key = (student.joining_date.year, student.joining_date.month)
    current_key = (today.year, today.month)
    target_key = (year, month)

    if target_key < joining_key:
        return {'code': 'before', 'payment': payment, 'is_advance': False}
    if target_key > current_key:
        if payment:
            return {'code': 'paid', 'payment': payment, 'is_advance': True}
        return {'code': 'future', 'payment': None, 'is_advance': False}
    if payment:
        return {'code': 'paid', 'payment': payment, 'is_advance': False}
    return {'code': 'unpaid', 'payment': None, 'is_advance': False}


def build_ledger_row(student, current_year, today):
    payments = paid_lookup(student, current_year)
    row = {
        'student': student,
        'months': [],
        'paid_count': 0,
        'advance_count': 0,
        'unpaid_count': 0,
        'due_amount': Decimal('0.00'),
    }

    for month_num in range(1, 13):
        status = get_month_status(student, current_year, month_num, today, payments)
        row['months'].append(status['code'])
        if status['code'] == 'paid':
            row['paid_count'] += 1
            if status['is_advance']:
                row['advance_count'] += 1
        elif status['code'] == 'unpaid':
            row['unpaid_count'] += 1

    row['due_amount'] = student.monthly_fee * row['unpaid_count']
    return row


def overdue_summary(student, today):
    payments = paid_lookup(student)
    month_cursor = student.joining_date.month
    year_cursor = student.joining_date.year
    overdue_months = []

    while (year_cursor, month_cursor) <= (today.year, today.month):
        if (year_cursor, month_cursor) not in payments:
            overdue_months.append(month_label(year_cursor, month_cursor))
        if month_cursor == 12:
            month_cursor = 1
            year_cursor += 1
        else:
            month_cursor += 1

    total_due = student.monthly_fee * len(overdue_months)
    return {
        'unpaid_count': len(overdue_months),
        'due_amount': total_due,
        'months': overdue_months,
    }


def monthly_report_rows(students, year, month, today):
    rows = []
    total_paid = Decimal('0.00')
    total_due = Decimal('0.00')

    for student in students:
        payments = paid_lookup(student, year)
        status = get_month_status(student, year, month, today, payments)
        payment = status['payment']

        if status['code'] == 'paid':
            status_label = 'Paid Ahead' if status['is_advance'] else 'Paid'
            amount_paid = payment.amount or student.monthly_fee
            due_amount = Decimal('0.00')
            payment_method = payment.payment_method
            paid_on = payment.paid_on
            total_paid += amount_paid
        elif status['code'] == 'unpaid':
            status_label = 'Overdue'
            amount_paid = Decimal('0.00')
            due_amount = student.monthly_fee
            payment_method = '-'
            paid_on = None
            total_due += due_amount
        elif status['code'] == 'future':
            status_label = 'Upcoming'
            amount_paid = Decimal('0.00')
            due_amount = Decimal('0.00')
            payment_method = '-'
            paid_on = None
        else:
            status_label = 'Not Joined'
            amount_paid = Decimal('0.00')
            due_amount = Decimal('0.00')
            payment_method = '-'
            paid_on = None

        rows.append({
            'student': student,
            'status': status_label,
            'amount_paid': amount_paid,
            'due_amount': due_amount,
            'payment_method': payment_method,
            'paid_on': paid_on,
        })

    return rows, total_paid, total_due


def yearly_report_rows(students, year, today):
    rows = []
    total_paid = Decimal('0.00')
    total_due = Decimal('0.00')

    for student in students:
        ledger_row = build_ledger_row(student, year, today)
        payments = paid_lookup(student, year)
        paid_amount = sum(
            (payment.amount or student.monthly_fee)
            for payment in payments.values()
        )
        total_paid += paid_amount
        total_due += ledger_row['due_amount']
        rows.append({
            'student': student,
            'paid_months': ledger_row['paid_count'],
            'advance_months': ledger_row['advance_count'],
            'overdue_months': ledger_row['unpaid_count'],
            'paid_amount': paid_amount,
            'due_amount': ledger_row['due_amount'],
        })

    return rows, total_paid, total_due


def normalize_phone_number(contact):
    digits = ''.join(ch for ch in contact if ch.isdigit())
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def monthly_reminder_rows(students, today):
    rows = []
    current_label = month_label(today.year, today.month)

    for student in students:
        payments = paid_lookup(student, today.year)
        current_status = get_month_status(student, today.year, today.month, today, payments)
        if current_status['code'] != 'unpaid':
            continue

        overdue = overdue_summary(student, today)
        months_text = ', '.join(overdue['months'])
        message = (
            f"Hello {student.name}, this is your {current_label} fee reminder from "
            f"Valmiki Library. Your pending dues are ₹{overdue['due_amount']} for "
            f"{overdue['unpaid_count']} month(s): {months_text}. Please pay soon."
        )
        phone_number = normalize_phone_number(student.contact)

        rows.append({
            'student': student,
            'due_amount': overdue['due_amount'],
            'overdue_months': overdue['unpaid_count'],
            'overdue_labels': overdue['months'],
            'message': message,
            'whatsapp_url': f"https://wa.me/{phone_number}?text={quote(message)}" if phone_number else '',
        })

    rows.sort(key=lambda row: row['due_amount'], reverse=True)
    return rows
