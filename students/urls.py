from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.dashboard,      name='dashboard'),      # ← CHANGED
    path('students/',               views.student_list,   name='student_list'),   # ← CHANGED
    path('add/',                    views.add_student,    name='add_student'),
    path('delete/<int:pk>/',        views.delete_student, name='delete_student'),
    path('seats/',                  views.seating_chart,  name='seating_chart'),
    path('ledger/',                 views.payment_ledger, name='payment_ledger'),
    path('mark/<int:student_id>/<int:month>/<int:year>/',
                                    views.mark_payment,   name='mark_payment'),
    path('defaulters/',             views.defaulters,     name='defaulters'),
    path('export/', views.export_students_excel, name='export_students_excel'),
]