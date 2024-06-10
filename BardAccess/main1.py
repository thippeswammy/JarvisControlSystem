BARD_API_KEY = "dwgCX0zBvQq-OciSUP7M2AFg0nZxNgjqCudd57mZMMXYMpqwbFBmbmfZVAyOqzS5bJEefA."

from bardapi import Bard

token = BARD_API_KEY

bard = Bard(token=token)

result = bard.get_answer("what is 2+2")

print(result)
