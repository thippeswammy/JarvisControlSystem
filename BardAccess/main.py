# AIzaSyABmEj2MAVGCx8-6rzSEfmSmUVBM1KtgF0
import os

from bardapi import Bard

os.environ["_BARD_API_KEY"] = "dwgCX0zBvQq-OciSUP7M2AFg0nZxNgjqCudd57mZMMXYMpqwbFBmbmfZVAyOqzS5bJEefA."

message = input("enter your prompt:")

print(Bard().get_answer(str(message)))
