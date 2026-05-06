from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Mentor, MentorshipSession, Payment, Student
from .views import build_mentor_verification_token, build_student_verification_token


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 5, 5)


class PublicMarketingTests(TestCase):
    def test_public_landing_page_is_visible_and_links_to_library_access(self):
        response = self.client.get(reverse('marketing_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Library Management')
        self.assertContains(response, 'name="library"')
        self.assertContains(response, reverse('login'))
        self.assertContains(response, 'Choose your plan')

    def test_login_page_shows_selected_library_name(self):
        response = self.client.get(reverse('login'), {'library': 'Bright Study Room'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bright Study Room')
        self.assertContains(response, 'Workspace requested')

    def test_admin_login_redirects_to_dashboard_route(self):
        User.objects.create_user(username='portal-admin', password='secret123')

        response = self.client.post(
            reverse('login'),
            {'username': 'portal-admin', 'password': 'secret123'},
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_library_access_request_sends_email_to_owner_mail(self):
        response = self.client.post(
            reverse('marketing_home'),
            {
                'library': 'Bright Study Room',
                'requester_name': 'Ritu Raj',
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('marketing_home')}?library=Bright+Study+Room&requester_name=Ritu+Raj",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['realjyotish0001@gmail.com'])
        self.assertIn('Bright Study Room', mail.outbox[0].subject)
        self.assertIn('Ritu Raj', mail.outbox[0].body)


class SeatingChartStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='secret123')
        self.client.login(username='admin', password='secret123')

    def test_seating_chart_uses_expected_status_colors(self):
        morning_student = Student.objects.create(
            name='Morning Student',
            contact='9999999991',
            seat_number='10',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )
        Student.objects.create(
            name='Evening Student',
            contact='9999999992',
            seat_number='11',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )
        Student.objects.create(
            name='Evening Student Two',
            contact='9999999993',
            seat_number='11',
            shift='Evening',
            joining_date=date(2026, 1, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )
        Student.objects.create(
            name='Full Day Student',
            contact='9999999994',
            seat_number='12',
            shift='Full Day',
            joining_date=date(2026, 1, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )

        response = self.client.get(reverse('seating_chart'))

        self.assertContains(response, 'class="seat partially-vacant"')
        self.assertContains(response, 'class="seat fully-occupied"')
        self.assertContains(response, 'class="seat full-day"')
        self.assertContains(response, '1 vacant')
        self.assertContains(response, 'occupied')
        self.assertContains(response, 'full day')
        self.assertContains(response, reverse('edit_student', args=[morning_student.pk]))

    def test_student_detail_page_shows_seat_wise_details_and_vacant_seats(self):
        student = Student.objects.create(
            name='Seat Detail Student',
            contact='8888888881',
            email='seatdetail@student.com',
            seat_number='25',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=700,
            monthly_due_day=6,
            mode_of_payment='UPI',
            preparing_for='SSC',
            academic_details='B.A. second year',
            status='Active',
        )

        response = self.client.get(reverse('student_detail'))

        self.assertContains(response, 'Seat 25')
        self.assertContains(response, 'Seat Detail Student')
        self.assertContains(response, 'Vacant seat available for assignment.')
        self.assertContains(response, reverse('edit_student', args=[student.pk]))

    def test_student_detail_page_shows_receipt_export_for_paid_students(self):
        student = Student.objects.create(
            name='Receipt Detail Student',
            contact='8888888882',
            seat_number='26',
            shift='Evening',
            joining_date=date(2026, 1, 1),
            monthly_fee=650,
            mode_of_payment='Cash',
        )
        payment = Payment.objects.create(
            student=student,
            month=5,
            year=2026,
            is_paid=True,
            amount=650,
            payment_method='Cash',
            paid_on=date(2026, 5, 5),
        )

        response = self.client.get(reverse('student_detail'))

        self.assertContains(response, 'Latest paid receipt')
        self.assertContains(response, payment.month_label)
        self.assertContains(response, reverse('payment_receipt_pdf', args=[payment.pk]))


class PaymentLedgerSummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ledger-admin', password='secret123')
        self.client.login(username='ledger-admin', password='secret123')

    @patch('students.views.date', FixedDate)
    def test_future_months_do_not_create_false_dues(self):
        student = Student.objects.create(
            name='Ledger Student',
            contact='9999999995',
            seat_number='15',
            shift='Morning',
            joining_date=date(2026, 5, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )
        Payment.objects.create(
            student=student,
            month=5,
            year=2026,
            is_paid=True,
            amount=500,
        )
        Payment.objects.create(
            student=student,
            month=6,
            year=2026,
            is_paid=True,
            amount=500,
        )

        response = self.client.get(reverse('payment_ledger'), {'year': 2026})

        self.assertContains(response, '2 paid months')
        self.assertContains(response, '1 month paid ahead')
        self.assertContains(response, 'No dues')
        self.assertContains(response, 'Record advance payment')

    @patch('students.views.date', FixedDate)
    def test_due_column_only_counts_overdue_months_up_to_today(self):
        student = Student.objects.create(
            name='Due Student',
            contact='9999999996',
            seat_number='16',
            shift='Evening',
            joining_date=date(2026, 3, 1),
            monthly_fee=500,
            mode_of_payment='Cash',
        )
        Payment.objects.create(
            student=student,
            month=3,
            year=2026,
            is_paid=True,
            amount=500,
        )

        response = self.client.get(reverse('payment_ledger'), {'year': 2026})

        self.assertContains(response, '2 overdue months')
        self.assertContains(response, '₹1000')


class PaymentReceiptAndReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='finance-admin', password='secret123')
        self.client.login(username='finance-admin', password='secret123')

    @patch('students.views.date', FixedDate)
    def test_payment_entry_saves_method_amount_and_receipt_downloads(self):
        student = Student.objects.create(
            name='Receipt Student',
            contact='9999999997',
            seat_number='21',
            shift='Morning',
            joining_date=date(2026, 5, 1),
            monthly_fee=750,
            mode_of_payment='Cash',
        )

        response = self.client.post(
            reverse('payment_entry', args=[student.pk, 2026, 5]),
            {
                'payment_method': 'UPI',
                'amount': '750',
                'paid_on': '2026-05-05',
                'action': 'save_and_receipt',
            },
        )

        payment = Payment.objects.get(student=student, year=2026, month=5)
        self.assertTrue(payment.is_paid)
        self.assertEqual(payment.payment_method, 'UPI')
        self.assertEqual(payment.amount, student.monthly_fee)
        self.assertRedirects(response, reverse('payment_receipt_pdf', args=[payment.pk]))

        receipt_response = self.client.get(reverse('payment_receipt_pdf', args=[payment.pk]))
        self.assertEqual(receipt_response.status_code, 200)
        self.assertEqual(receipt_response['Content-Type'], 'application/pdf')
        self.assertTrue(receipt_response.content.startswith(b'%PDF'))

    @patch('students.views.date', FixedDate)
    def test_monthly_report_excel_export_downloads(self):
        student = Student.objects.create(
            name='Report Student',
            contact='9999999998',
            seat_number='22',
            shift='Evening',
            joining_date=date(2026, 4, 1),
            monthly_fee=500,
            mode_of_payment='Online',
        )
        Payment.objects.create(
            student=student,
            month=5,
            year=2026,
            is_paid=True,
            amount=500,
            payment_method='Online',
        )

        response = self.client.get(
            reverse('export_report'),
            {'scope': 'monthly', 'format': 'xlsx', 'year': 2026, 'month': 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('monthly-report-2026-05.xlsx', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'PK'))

    @patch('students.views.date', FixedDate)
    def test_monthly_reminders_page_shows_due_students_and_whatsapp_link(self):
        due_student = Student.objects.create(
            name='Reminder Student',
            contact='9999999990',
            seat_number='23',
            shift='Full Day',
            joining_date=date(2026, 4, 1),
            monthly_fee=600,
            mode_of_payment='Cash',
        )
        Payment.objects.create(
            student=due_student,
            month=4,
            year=2026,
            is_paid=True,
            amount=600,
            payment_method='Cash',
        )

        response = self.client.get(reverse('monthly_reminders'))

        self.assertContains(response, 'Reminder Student')
        self.assertContains(response, '₹600')
        self.assertContains(response, 'wa.me/919999999990')


class StudentPortalTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name='Portal Student',
            contact='9999999991',
            email='portal@student.com',
            date_of_birth=date(2005, 1, 15),
            seat_number='30',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=800,
            monthly_due_day=7,
            mode_of_payment='UPI',
            preparing_for='UPSC',
            academic_details='B.A. final year',
            emergency_contact_name='Parent',
            emergency_contact_phone='8888888888',
            status='Active',
        )

    def test_student_portal_can_send_verification_email(self):
        response = self.client.post(
            reverse('student_portal_login'),
            {
                'name': self.student.name,
                'email': self.student.email,
                'contact': self.student.contact,
                'date_of_birth': self.student.date_of_birth.isoformat(),
                'action': 'send_verification',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your Valmiki Library student account', mail.outbox[0].subject)
        self.assertContains(response, 'Verification email sent')

    def test_student_can_verify_and_login_with_profile_details(self):
        token = build_student_verification_token(self.student)

        verify_response = self.client.get(reverse('student_verify_email', args=[token]))
        self.assertRedirects(verify_response, f"{reverse('student_portal_login')}?verified=1")

        self.student.refresh_from_db()
        self.assertTrue(self.student.email_verified)

        login_response = self.client.post(
            reverse('student_portal_login'),
            {
                'name': self.student.name,
                'email': self.student.email,
                'contact': self.student.contact,
                'date_of_birth': self.student.date_of_birth.isoformat(),
                'action': 'login',
            },
        )

        self.assertRedirects(login_response, reverse('student_portal_dashboard'))

        dashboard_response = self.client.get(reverse('student_portal_dashboard'))
        self.assertContains(dashboard_response, 'Portal Student')
        self.assertContains(dashboard_response, 'UPSC')
        self.assertContains(dashboard_response, 'B.A. final year')

    def test_student_portal_receipt_access_is_limited_to_their_own_payment(self):
        self.student.email_verified = True
        self.student.save(update_fields=['email_verified'])
        payment = Payment.objects.create(
            student=self.student,
            month=5,
            year=2026,
            is_paid=True,
            amount=800,
            payment_method='UPI',
            paid_on=date(2026, 5, 5),
        )

        self.client.post(
            reverse('student_portal_login'),
            {
                'name': self.student.name,
                'email': self.student.email,
                'contact': self.student.contact,
                'date_of_birth': self.student.date_of_birth.isoformat(),
                'action': 'login',
            },
        )

        receipt_response = self.client.get(reverse('payment_receipt_pdf', args=[payment.pk]))
        self.assertEqual(receipt_response.status_code, 200)
        self.assertEqual(receipt_response['Content-Type'], 'application/pdf')


class MentorPortalTests(TestCase):
    def setUp(self):
        self.mentor = Mentor.objects.create(
            name='Mentor One',
            email='mentor@example.com',
            contact='9876543210',
            job_role='UPSC Mentor',
            current_work='Runs live answer-writing sessions',
            experience_years=6,
            streams_known='UPSC GS, interview preparation, essay guidance',
            primary_session_mode='Daily',
            daily_session_price=700,
            monthly_session_price=3000,
        )
        self.student = Student.objects.create(
            name='Mentorship Student',
            contact='9999999988',
            email='mentee@example.com',
            date_of_birth=date(2004, 7, 10),
            seat_number='44',
            shift='Evening',
            joining_date=date(2026, 1, 1),
            monthly_fee=800,
            mode_of_payment='UPI',
            preparing_for='UPSC',
            academic_details='B.Sc. graduate',
            status='Active',
            email_verified=True,
        )

    def test_mentor_portal_can_register_and_send_verification_email(self):
        response = self.client.post(
            reverse('mentor_portal_register'),
            {
                'name': 'New Mentor',
                'email': 'newmentor@example.com',
                'contact': '9123456789',
                'job_role': 'SSC Mentor',
                'current_work': 'Teaches reasoning and maths',
                'experience_years': 4,
                'streams_known': 'SSC, railway, quant practice',
                'bio': 'Helps students revise through rapid-fire questioning.',
                'primary_session_mode': 'Monthly',
                'daily_session_price': '400',
                'monthly_session_price': '2200',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Mentor.objects.filter(email='newmentor@example.com').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your Valmiki Library mentor account', mail.outbox[0].subject)
        self.assertContains(response, 'Mentor profile created')

    def test_mentor_can_verify_login_and_update_session(self):
        token = build_mentor_verification_token(self.mentor)

        verify_response = self.client.get(reverse('mentor_verify_email', args=[token]))
        self.assertRedirects(verify_response, f"{reverse('mentor_portal_login')}?verified=1")

        self.mentor.refresh_from_db()
        self.assertTrue(self.mentor.email_verified)

        login_response = self.client.post(
            reverse('mentor_portal_login'),
            {
                'email': self.mentor.email,
                'contact': self.mentor.contact,
                'action': 'login',
            },
        )
        self.assertRedirects(login_response, reverse('mentor_portal_dashboard'))

        session = MentorshipSession.objects.create(
            student=self.student,
            mentor=self.mentor,
            plan_type='Daily',
            topic='Modern History revision',
            student_study_notes='Revised spectrum chapters 1 to 5',
            preparation_target='UPSC',
            preferred_date=date(2026, 5, 8),
            price=700,
        )

        detail_response = self.client.post(
            reverse('mentor_session_detail', args=[session.pk]),
            {
                'status': 'Completed',
                'meeting_link': 'https://meet.google.com/test-session',
                'mentor_questions': 'Asked 10 questions from revolt of 1857.',
                'mentor_feedback': 'Needs sharper recall on causes and consequences.',
                'price': '700',
                'marks_awarded': '8.5',
            },
        )

        self.assertRedirects(detail_response, reverse('mentor_session_detail', args=[session.pk]))

        session.refresh_from_db()
        self.assertEqual(session.status, 'Completed')
        self.assertEqual(session.meeting_link, 'https://meet.google.com/test-session')
        self.assertEqual(session.marks_awarded, Decimal('8.50'))
        self.assertIn('Needs sharper recall', session.mentor_feedback)


class StudentMentorshipPortalTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name='Booked Student',
            contact='9999999977',
            email='booked@student.com',
            date_of_birth=date(2005, 2, 14),
            seat_number='55',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=900,
            mode_of_payment='Online',
            preparing_for='Banking',
            academic_details='B.Com. second year',
            status='Active',
            email_verified=True,
        )
        self.mentor = Mentor.objects.create(
            name='Practice Mentor',
            email='practice.mentor@example.com',
            contact='9000000001',
            job_role='Banking Interview Mentor',
            current_work='Conducts aptitude and interview sessions',
            experience_years=5,
            streams_known='Banking, interview prep, quantitative aptitude',
            primary_session_mode='Daily',
            daily_session_price=450,
            monthly_session_price=1800,
            email_verified=True,
            is_active=True,
        )

        self.client.post(
            reverse('student_portal_login'),
            {
                'name': self.student.name,
                'email': self.student.email,
                'contact': self.student.contact,
                'date_of_birth': self.student.date_of_birth.isoformat(),
                'action': 'login',
            },
        )

    def test_student_can_request_mentorship_session(self):
        response = self.client.post(
            reverse('student_portal_mentorship'),
            {
                'mentor_id': self.mentor.pk,
                'plan_type': 'Daily',
                'topic': 'Quant speed practice',
                'student_study_notes': 'Finished percentage and profit-loss formulas.',
                'preparation_target': 'Banking',
                'preferred_date': '2026-05-09',
            },
        )

        self.assertRedirects(response, reverse('student_portal_mentorship'))
        session = MentorshipSession.objects.get(student=self.student, mentor=self.mentor)
        self.assertEqual(session.topic, 'Quant speed practice')
        self.assertEqual(session.price, self.mentor.daily_session_price)
        self.assertEqual(session.status, 'Requested')

        page_response = self.client.get(reverse('student_portal_mentorship'))
        self.assertContains(page_response, 'Practice Mentor')
        self.assertContains(page_response, 'Quant speed practice')
