from generator.script import generate_script
try:
    print("Generating script...")
    data = generate_script(research={"text": "Tardigrades", "source": "Reddit"})
    print(data["title"])
except Exception as e:
    print(e)
