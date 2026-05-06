from datetime import date

from django.db import models
from django.core.exceptions import ValidationError

class Student(models.Model):
    SHIFT_CHOICES = [
        ('Morning', 'Morning'),
        ('Evening', 'Evening'),
        ('Full Day', 'Full Day'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('On Hold', 'On Hold'),
        ('Left', 'Left'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Online', 'Online'),
    ]

    name         = models.CharField(max_length=100)
    contact      = models.CharField(max_length=10)
    email        = models.EmailField(blank=True, null=True, unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    seat_number  = models.CharField(max_length=3)
    shift        = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    joining_date = models.DateField()
    monthly_fee  = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    monthly_due_day = models.PositiveSmallIntegerField(default=5)
    mode_of_payment = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='Cash')
    preparing_for = models.CharField(max_length=150, blank=True)
    academic_details = models.TextField(blank=True)
    profile_photo = models.FileField(upload_to='student_profiles/photos/', blank=True, null=True)
    id_copy = models.FileField(upload_to='student_profiles/id_copies/', blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    email_verified = models.BooleanField(default=False)

    def clean(self):
        existing_students = Student.objects.filter(seat_number=self.seat_number)

        if self.pk:
            existing_students = existing_students.exclude(pk=self.pk)

        shifts = [s.shift for s in existing_students]

        if 'Full Day' in shifts:
            raise ValidationError("Seat already occupied for Full Day")

        if self.shift == 'Full Day' and existing_students.exists():
            raise ValidationError("Cannot assign Full Day to occupied seat")

        if len(shifts) >= 2:
            raise ValidationError("Seat already has Morning & Evening")

        if self.shift in shifts:
            raise ValidationError(f"{self.shift} already exists for this seat")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.seat_number} - {self.shift})"


# ✅ IMPORTANT: This must be OUTSIDE Student class
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Online', 'Online'),
    ]

    student  = models.ForeignKey(Student, on_delete=models.CASCADE)
    month    = models.IntegerField()
    year     = models.IntegerField()
    is_paid  = models.BooleanField(default=False)
    paid_on  = models.DateField(null=True, blank=True)
    amount   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='Cash')

    @property
    def receipt_number(self):
        payment_id = self.pk or 0
        return f"VL-{self.year}{self.month:02d}-{payment_id:05d}"

    @property
    def month_label(self):
        return date(self.year, self.month, 1).strftime('%B %Y')

    def __str__(self):
        return f"{self.student.name} - {self.month}/{self.year}"


class Mentor(models.Model):
    SESSION_MODE_CHOICES = [
        ('Daily', 'Daily'),
        ('Monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=15, blank=True)
    job_role = models.CharField(max_length=120)
    current_work = models.CharField(max_length=150, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    streams_known = models.TextField(help_text="Subjects, streams, or exams the mentor can handle")
    bio = models.TextField(blank=True)
    primary_session_mode = models.CharField(max_length=20, choices=SESSION_MODE_CHOICES, default='Daily')
    daily_session_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_session_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    profile_photo = models.FileField(upload_to='mentor_profiles/photos/', blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.job_role})"


class MentorshipSession(models.Model):
    STATUS_CHOICES = [
        ('Requested', 'Requested'),
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PLAN_CHOICES = [
        ('Daily', 'Daily'),
        ('Monthly', 'Monthly'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='mentorship_sessions')
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='mentorship_sessions')
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default='Daily')
    topic = models.CharField(max_length=180)
    student_study_notes = models.TextField(blank=True)
    preparation_target = models.CharField(max_length=180, blank=True)
    preferred_date = models.DateField(blank=True, null=True)
    meeting_link = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    mentor_questions = models.TextField(blank=True)
    mentor_feedback = models.TextField(blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.name} with {self.mentor.name} ({self.topic})"
