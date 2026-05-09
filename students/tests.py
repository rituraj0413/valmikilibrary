import hashlib
import hmac
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Mentor, MentorshipSession, Payment, PortalMessage, Student, StudentOnlinePayment
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

    def test_admin_can_reply_to_student_from_student_detail_message_center(self):
        student = Student.objects.create(
            name='Message Detail Student',
            contact='8888888891',
            seat_number='27',
            shift='Morning',
            joining_date=date(2026, 1, 1),
            monthly_fee=600,
            mode_of_payment='UPI',
        )

        response = self.client.post(
            reverse('admin_student_message', args=[student.pk]),
            {
                'body': 'Please share the payment screenshot here.',
            },
        )

        self.assertRedirects(response, f"{reverse('student_detail')}#student-{student.pk}")
        message = PortalMessage.objects.get(student=student)
        self.assertEqual(message.sender_role, 'Admin')
        self.assertIn('payment screenshot', message.body)

    def test_message_center_page_shows_student_conversation_and_admin_reply(self):
        student = Student.objects.create(
            name='Chat Student',
            contact='8888888892',
            seat_number='28',
            shift='Evening',
            joining_date=date(2026, 1, 1),
            monthly_fee=650,
            mode_of_payment='Online',
        )
        PortalMessage.objects.create(
            student=student,
            sender_role='Student',
            sender_name=student.name,
            body='I have sent the payment screenshot. Please confirm.',
        )

        response = self.client.get(reverse('message_center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages')
        self.assertContains(response, 'Chat Student')
        self.assertContains(response, 'payment screenshot')

        reply_response = self.client.post(
            reverse('admin_student_message', args=[student.pk]),
            {
                'body': 'Payment confirmed from admin side.',
                'next': f"{reverse('message_center')}?student={student.pk}",
            },
        )

        self.assertRedirects(reply_response, f"{reverse('message_center')}?student={student.pk}")
        self.assertTrue(
            PortalMessage.objects.filter(
                student=student,
                sender_role='Admin',
                body__icontains='Payment confirmed',
            ).exists()
        )


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

    def test_student_dashboard_shows_qr_payment_and_message_section(self):
        self.student.email_verified = True
        self.student.payment_qr = SimpleUploadedFile('student-qr.png', b'fake-qr-image', content_type='image/png')
        self.student.save(update_fields=['email_verified', 'payment_qr'])

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

        response = self.client.get(reverse('student_portal_dashboard'))

        self.assertContains(response, 'Online Payment & QR')
        self.assertContains(response, 'Message Admin')
        self.assertContains(response, 'Open QR')

    def test_student_can_send_message_with_attachment_to_admin(self):
        self.student.email_verified = True
        self.student.save(update_fields=['email_verified'])

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

        response = self.client.post(
            reverse('student_portal_message'),
            {
                'body': 'I have paid by QR. Please check my screenshot.',
                'attachment': SimpleUploadedFile('payment-proof.png', b'proof', content_type='image/png'),
            },
        )

        self.assertRedirects(response, reverse('student_portal_dashboard'))
        portal_message = PortalMessage.objects.get(student=self.student)
        self.assertEqual(portal_message.sender_role, 'Student')
        self.assertIn('paid by QR', portal_message.body)
        self.assertIn('payment-proof', portal_message.attachment.name)

    @override_settings(
        RAZORPAY_ENABLED=True,
        RAZORPAY_KEY_ID='rzp_test_123',
        RAZORPAY_KEY_SECRET='secret456',
        RAZORPAY_CURRENCY='INR',
    )
    @patch('students.views.create_razorpay_order')
    def test_student_can_create_razorpay_order_from_portal(self, mocked_create_order):
        self.student.email_verified = True
        self.student.save(update_fields=['email_verified'])
        mocked_create_order.return_value = {
            'id': 'order_test_123',
            'amount': 160000,
            'currency': 'INR',
        }

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

        response = self.client.post(
            reverse('student_portal_create_online_payment'),
            {'months': '2'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                'key': 'rzp_test_123',
                'order_id': 'order_test_123',
                'amount': 160000,
                'currency': 'INR',
                'description': 'Library fee payment for 2 months',
                'student_name': self.student.name,
                'student_email': self.student.email,
                'student_contact': self.student.contact,
                'seat_number': self.student.seat_number,
                'library_name': 'Valmiki Library',
                'months_requested': 2,
            },
        )
        online_payment = StudentOnlinePayment.objects.get(student=self.student, razorpay_order_id='order_test_123')
        self.assertEqual(online_payment.amount, Decimal('1600.00'))
        self.assertEqual(online_payment.months_covered, 2)

    @override_settings(
        RAZORPAY_ENABLED=True,
        RAZORPAY_KEY_ID='rzp_test_123',
        RAZORPAY_KEY_SECRET='secret456',
        RAZORPAY_CURRENCY='INR',
    )
    def test_student_online_payment_verification_marks_months_paid(self):
        self.student.email_verified = True
        self.student.save(update_fields=['email_verified'])

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

        StudentOnlinePayment.objects.create(
            student=self.student,
            amount=Decimal('1600.00'),
            currency='INR',
            purpose='Library fee payment for 2 months',
            months_covered=2,
            razorpay_order_id='order_test_456',
        )
        signature = hmac.new(
            b'secret456',
            b'order_test_456|pay_test_456',
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            reverse('student_portal_verify_online_payment'),
            {
                'razorpay_order_id': 'order_test_456',
                'razorpay_payment_id': 'pay_test_456',
                'razorpay_signature': signature,
            },
        )

        self.assertEqual(response.status_code, 200)
        online_payment = StudentOnlinePayment.objects.get(razorpay_order_id='order_test_456')
        self.assertEqual(online_payment.status, 'paid')
        self.assertEqual(
            Payment.objects.filter(student=self.student, is_paid=True, payment_method='Online').count(),
            2,
        )


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
                'status': 'Scheduled',
                'preferred_date': '2026-05-09',
                'scheduled_time': '18:30',
                'meeting_link': 'https://meet.google.com/test-session',
                'mentor_questions': 'Asked 10 questions from revolt of 1857.',
                'mentor_feedback': 'Needs sharper recall on causes and consequences.',
                'price': '700',
                'marks_awarded': '8.5',
            },
        )

        self.assertRedirects(detail_response, reverse('mentor_session_detail', args=[session.pk]))

        session.refresh_from_db()
        self.assertEqual(session.status, 'Scheduled')
        self.assertEqual(session.meeting_link, 'https://meet.google.com/test-session')
        self.assertEqual(session.preferred_date, date(2026, 5, 9))
        self.assertEqual(session.scheduled_time, time(18, 30))
        self.assertEqual(session.marks_awarded, Decimal('8.50'))
        self.assertIn('Needs sharper recall', session.mentor_feedback)
        self.assertContains(self.client.get(reverse('mentor_session_detail', args=[session.pk])), reverse('mentorship_session_room', args=[session.pk]))

    def test_mentor_can_email_join_details_to_student(self):
        self.mentor.email_verified = True
        self.mentor.save(update_fields=['email_verified'])

        self.client.post(
            reverse('mentor_portal_login'),
            {
                'email': self.mentor.email,
                'contact': self.mentor.contact,
                'action': 'login',
            },
        )

        session = MentorshipSession.objects.create(
            student=self.student,
            mentor=self.mentor,
            plan_type='Daily',
            topic='Economy revision room',
            student_study_notes='Revised inflation and fiscal deficit topics.',
            preparation_target='UPSC',
            preferred_date=date(2026, 5, 12),
            scheduled_time=time(19, 45),
            price=700,
        )

        response = self.client.post(
            reverse('mentor_session_detail', args=[session.pk]),
            {
                'action': 'save_and_email',
                'status': 'Scheduled',
                'preferred_date': '2026-05-12',
                'scheduled_time': '19:45',
                'meeting_link': 'https://meet.google.com/economy-revision',
                'mentor_questions': 'Inflation, repo rate, and deficit questions.',
                'mentor_feedback': 'Good conceptual understanding.',
                'price': '700',
                'marks_awarded': '9.0',
            },
        )

        self.assertRedirects(response, reverse('mentor_session_detail', args=[session.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['mentee@example.com'])
        self.assertIn('Economy revision room', mail.outbox[0].subject)
        self.assertIn('https://meet.google.com/economy-revision', mail.outbox[0].body)
        self.assertIn(reverse('mentorship_session_room', args=[session.pk]), mail.outbox[0].body)


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

    def test_student_can_see_join_room_when_mentor_schedules_session(self):
        session = MentorshipSession.objects.create(
            student=self.student,
            mentor=self.mentor,
            plan_type='Daily',
            topic='Mock interview practice',
            student_study_notes='Revised HR answers and self-introduction.',
            preparation_target='Banking',
            preferred_date=date(2026, 5, 10),
            scheduled_time=time(19, 0),
            status='Scheduled',
            price=self.mentor.daily_session_price,
            meeting_link='https://meet.google.com/mock-interview',
        )

        page_response = self.client.get(reverse('student_portal_mentorship'))

        self.assertContains(page_response, 'Join Live VC Room')
        self.assertContains(page_response, reverse('mentorship_session_room', args=[session.pk]))
        self.assertContains(page_response, 'Join Google Meet')

    def test_student_can_open_embedded_session_room(self):
        session = MentorshipSession.objects.create(
            student=self.student,
            mentor=self.mentor,
            plan_type='Daily',
            topic='Aptitude revision room',
            student_study_notes='Need speed practice and oral questions.',
            preparation_target='Banking',
            preferred_date=date(2026, 5, 11),
            scheduled_time=time(17, 15),
            status='Scheduled',
            price=self.mentor.daily_session_price,
        )

        room_response = self.client.get(reverse('mentorship_session_room', args=[session.pk]))

        self.assertEqual(room_response.status_code, 200)
        self.assertContains(room_response, 'Live Mentorship Room')
        self.assertContains(room_response, session.live_room_name)
        self.assertContains(room_response, 'Booked Student')
