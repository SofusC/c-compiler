import cProfile
from src.compiler_driver import main

cProfile.run("main()", filename="profile.out")
