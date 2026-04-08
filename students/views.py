from django.db.models import Sum
from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect, get_object_or_404
from .models import Student, Payment
from django.contrib.auth.decorators import login_required

@login_required   # only logged-in admin can see this
def student_list(request):
    students = Student.objects.all()   # get all students from DB
    return render(request, 'students/student_list.html', {'students': students})

@login_required
def add_student(request):
    error = None

    if request.method == 'POST':
        name            = request.POST['name']
        contact         = request.POST['contact']
        seat_number     = request.POST['seat_number']
        shift           = request.POST['shift']
        joining_date    = request.POST['joining_date']
        monthly_fee     = request.POST['monthly_fee']
        mode_of_payment = request.POST['mode_of_payment']

        # Valid seats
        valid_seats = [str(i) for i in range(1, 101)]
        if seat_number not in valid_seats:
            error = f"❌ Seat {seat_number} invalid"
        else:
            existing_students = Student.objects.filter(seat_number=seat_number)
            shifts = [s.shift for s in existing_students]

            # ❌ Rule 1: Full Day already exists
            if 'Full Day' in shifts:
                error = "❌ Seat already occupied for Full Day"

            # ❌ Rule 2: Adding Full Day when seat already has students
            elif shift == 'Full Day' and existing_students.exists():
                error = "❌ Cannot assign Full Day to occupied seat"

            # ❌ Rule 3: Max 2 students
            elif len(shifts) >= 2:
                error = "❌ Seat already has Morning & Evening"

            # ❌ Rule 4: Duplicate shift
            elif shift in shifts:
                error = f"❌ {shift} already exists on this seat"

            else:
                Student.objects.create(
                    name=name,
                    contact=contact,
                    seat_number=seat_number,
                    shift=shift,
                    joining_date=joining_date,
                    monthly_fee=monthly_fee,
                    mode_of_payment=mode_of_payment,
                )
                return redirect('student_list')

    return render(request, 'students/add_student.html', {'error': error})

@login_required
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    return redirect('student_list')

@login_required
def seating_chart(request):
    students = Student.objects.all()

    # Build seat map: seat_number -> {'Morning': student, 'Evening': student, 'Full Day': student}
    seat_map = {}
    for student in students:
        sn = student.seat_number
        if sn not in seat_map:
            seat_map[sn] = {}
        seat_map[sn][student.shift] = student

    seat_numbers = [str(i) for i in range(1, 101)]

    return render(request, 'students/seating_chart.html', {
        'seat_map':     seat_map,
        'seat_numbers': seat_numbers,
    })

from datetime import date

@login_required
def payment_ledger(request):
    students = Student.objects.all()
    current_year = int(request.GET.get('year', date.today().year))
    
    months = ['Jan','Feb','Mar','Apr','May','Jun',
              'Jul','Aug','Sep','Oct','Nov','Dec']

    # Build payment grid for each student
    ledger = []
    for student in students:
        row = {'student': student, 'months': []}
        for month_num in range(1, 13):
            joining = student.joining_date
            # Months before joining = dash (not applicable)
            if current_year < joining.year or \
               (current_year == joining.year and month_num < joining.month):
                row['months'].append('before')
            else:
                payment = Payment.objects.filter(
                    student=student,
                    month=month_num,
                    year=current_year,
                    is_paid=True
                ).first()
                row['months'].append('paid' if payment else 'unpaid')
        ledger.append(row)

    return render(request, 'students/payment_ledger.html', {
        'ledger': ledger,
        'months': months,
        'current_year': current_year,
        'years': range(2023, date.today().year + 2),
    })


@login_required
def mark_payment(request, student_id, month, year):
    student = get_object_or_404(Student, pk=student_id)
    payment, created = Payment.objects.get_or_create(
        student=student, month=month, year=year
    )
    # Toggle: if paid mark unpaid, if unpaid mark paid
    payment.is_paid = not payment.is_paid
    payment.paid_on = date.today() if payment.is_paid else None
    payment.save()
    return redirect(f'/ledger/?year={year}')



@login_required
def defaulters(request):
    students = Student.objects.all()
    today = date.today()
    current_month = today.month
    current_year = today.year

    defaulter_list = []
    for student in students:
        # Check if current month is paid
        payment = Payment.objects.filter(
            student=student,
            month=current_month,
            year=current_year,
            is_paid=True
        ).first()

        if not payment:
            # Count total unpaid months since joining
            unpaid_count = 0
            check_year  = student.joining_date.year
            check_month = student.joining_date.month

            while (check_year, check_month) <= (current_year, current_month):
                p = Payment.objects.filter(
                    student=student,
                    month=check_month,
                    year=check_year,
                    is_paid=True
                ).first()
                if not p:
                    unpaid_count += 1
                if check_month == 12:
                    check_month = 1
                    check_year += 1
                else:
                    check_month += 1

            defaulter_list.append({
                'student': student,
                'unpaid_months': unpaid_count,
                'total_due': unpaid_count * student.monthly_fee,
            })

    # Sort by most due first
    defaulter_list.sort(key=lambda x: x['total_due'], reverse=True)

    return render(request, 'students/defaulters.html', {
        'defaulter_list': defaulter_list,
        'current_month': date.today().strftime('%B %Y'),
        'total_due_all': sum(d['total_due'] for d in defaulter_list),
    })



@login_required
def dashboard(request):
    today = date.today()
    total_students  = Student.objects.count()
    total_seats     = 100
    occupied_seats  = Student.objects.count()
    vacant_seats    = total_seats - occupied_seats

    morning_count   = Student.objects.filter(shift='Morning').count()
    evening_count   = Student.objects.filter(shift='Evening').count()
    fullday_count   = Student.objects.filter(shift='Full Day').count()

    # This month collections
    paid_this_month = Payment.objects.filter(
        month=today.month,
        year=today.year,
        is_paid=True
    ).count()

    # Defaulters this month
    defaulters_count = total_students - paid_this_month

    # Total revenue collected ever
    total_revenue = Payment.objects.filter(
        is_paid=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Recent 5 students added
    recent_students = Student.objects.order_by('-joining_date')[:5]

    return render(request, 'students/dashboard.html', {
        'total_students':  total_students,
        'vacant_seats':    vacant_seats,
        'occupied_seats':  occupied_seats,
        'morning_count':   morning_count,
        'evening_count':   evening_count,
        'fullday_count':   fullday_count,
        'paid_this_month': paid_this_month,
        'defaulters_count': defaulters_count,
        'total_revenue':   total_revenue,
        'recent_students': recent_students,
        'current_month':   today.strftime('%B %Y'),
    })





from django.db.models import Count

@login_required
def dashboard(request):
    today = date.today()
    total_students   = Student.objects.count()
    occupied_seats   = total_students
    vacant_seats     = 100 - occupied_seats
    morning_count    = Student.objects.filter(shift='Morning').count()
    evening_count    = Student.objects.filter(shift='Evening').count()
    fullday_count    = Student.objects.filter(shift='Full Day').count()

    paid_this_month  = Payment.objects.filter(
        month=today.month, year=today.year, is_paid=True).count()
    defaulters_count = total_students - paid_this_month

    # Earnings this month
    paid_students_this_month = Payment.objects.filter(
        month=today.month, year=today.year, is_paid=True
    ).select_related('student')

    monthly_earning = sum(
        p.student.monthly_fee for p in paid_students_this_month
    )

    # Expected total if everyone pays
    expected_monthly = sum(
        s.monthly_fee for s in Student.objects.all()
    )

    pending_amount = expected_monthly - monthly_earning

    # Cash vs Online breakdown
    cash_students   = Student.objects.filter(mode_of_payment='Cash').count()
    online_students = Student.objects.filter(mode_of_payment='Online').count()

    recent_students = Student.objects.order_by('-joining_date')[:5]

    return render(request, 'students/dashboard.html', {
        'total_students':    total_students,
        'vacant_seats':      vacant_seats,
        'occupied_seats':    occupied_seats,
        'morning_count':     morning_count,
        'evening_count':     evening_count,
        'fullday_count':     fullday_count,
        'paid_this_month':   paid_this_month,
        'defaulters_count':  defaulters_count,
        'monthly_earning':   monthly_earning,
        'expected_monthly':  expected_monthly,
        'pending_amount':    pending_amount,
        'cash_students':     cash_students,
        'online_students':   online_students,
        'recent_students':   recent_students,
        'current_month':     today.strftime('%B %Y'),
    })

from django.http import HttpResponse
import openpyxl

@login_required
def export_students_excel(request):
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    # Headers
    headers = [
        "Name", "Contact", "Seat", "Shift",
        "Joining Date", "Monthly Fee", "Payment Mode"
    ]
    ws.append(headers)

    # Get data
    students = Student.objects.all()

    for s in students:
        ws.append([
            s.name,
            s.contact,
            s.seat_number,
            s.shift,
            str(s.joining_date),
            float(s.monthly_fee),
            s.mode_of_payment
        ])

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=students.xlsx'

    wb.save(response)
    return response