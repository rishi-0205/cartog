"""Doctor command — callback only. PATTERN: CLI-DOCTOR-01."""
import typer
app = typer.Typer()

@app.callback()
def doctor():
    """Check the environment."""
    from cli.services.doctor_service import doctor_service
    doctor_service()
