from django.db import models

# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html


class Countries(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class States(models.Model):
    country = models.ForeignKey(Countries, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Cities(models.Model):
    country = models.ForeignKey(Countries, on_delete=models.CASCADE)
    state = models.ForeignKey(States, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name