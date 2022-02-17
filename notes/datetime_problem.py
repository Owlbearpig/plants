from datetime import datetime
s0 = "2022-02-14T12-39-11.698945"
s1 = "2022-02-15T11-59-58.911763"
s2 = "2022-02-15T13-17-44.924371"

t0 = datetime.strptime(s0, '%Y-%m-%dT%H-%M-%S.%f')
t1 = datetime.strptime(s1, '%Y-%m-%dT%H-%M-%S.%f')
t2 = datetime.strptime(s2, '%Y-%m-%dT%H-%M-%S.%f')

dt1 = t1 - t0
dt2 = t2 - t0

tt1 = dt1.seconds / 60 + 1440 * dt1.days
tt2 = dt2.seconds / 60 + 1440 * dt2.days
print(tt1)
print(tt2)

# -> there is no problem
