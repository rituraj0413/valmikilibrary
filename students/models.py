from django.db import models
from django.core.exceptions import ValidationError

class Student(models.Model):
    SHIFT_CHOICES = [
        ('Morning', 'Morning'),
        ('Evening', 'Evening'),
        ('Full Day', 'Full Day'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Online', 'Online'),
    ]

    name         = models.CharField(max_length=100)
    contact      = models.CharField(max_length=10)
    seat_number  = models.CharField(max_length=3)
    shift        = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    joining_date = models.DateField()
    monthly_fee  = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    mode_of_payment = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='Cash')

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
    student  = models.ForeignKey(Student, on_delete=models.CASCADE)
    month    = models.IntegerField()
    year     = models.IntegerField()
    is_paid  = models.BooleanField(default=False)
    paid_on  = models.DateField(null=True, blank=True)
    amount   = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.student.name} - {self.month}/{self.year}"