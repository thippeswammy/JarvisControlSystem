from bardapi import Bard

bard = Bard()
bard.set_api_key("AIzaSyABmEj2MAVGCx8-6rzSEfmSmUVBM1KtgF0")

message = input("enter your prompt:")

print(bard.get_answer(str(message)))
