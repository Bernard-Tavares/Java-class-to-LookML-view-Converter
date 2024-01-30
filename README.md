README for Java to LookML Converter
Overview
This project includes a Python script designed to automate the conversion of Java class files into LookML view files. Primarily focused on processing Java files for Looker projects, it extracts relevant metadata and annotations from Java files and generates corresponding LookML code.

Features
Java File Processing: Reads Java files from a specified directory, filtering based on specific criteria (e.g., excluding files with certain names or phrases).
Classification and Prioritization: Classifies Java files into 'public class' and 'public abstract class', processing them in a defined order.
Annotation Extraction: Extracts annotations, properties, and table names from Java class files.
LookML Generation: Generates LookML view code based on extracted Java file information.
Base Class Check: Verifies if the base class for a Java file has a corresponding LookML file generated.
Output Management: Saves generated LookML code into specified directory.
Usage Summary
Setup: Clone the repository and navigate to the project directory.
Configuration: Modify the source_folder and destination_folder in the script to point to your Java files' location and where you want the LookML files saved, respectively.
Running the Script:
Execute the script using a Python interpreter. This can be done through a command line interface or an integrated development environment (IDE).
The script will process the Java files in the specified source directory, generating LookML files in the destination directory.
Git Integration:
After generating LookML files, you can push these to your Git repository which is integrated with your Looker project.
Use standard Git commands (git add, git commit, git push) to add, commit, and push the LookML files to your repository.
Note
Ensure that Python is installed on your system to run the script.
Familiarity with basic Git operations is recommended for managing LookML files within a version-controlled environment.
