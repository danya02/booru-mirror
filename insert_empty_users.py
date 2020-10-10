from database import *
for i in range(750953):
    try:
        print(i)
        User.create(id=i)
    except:
        pass
