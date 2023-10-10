import csv

input_file = 'C:/Users/jacso/Desktop/Diseratie/Database/creditcard.csv'
output_file = 'C:/Users/jacso/Desktop/Diseratie/Database/creditcard1.csv'
start_line = 5000
end_line = 284807

with open(input_file, 'r') as file_in, open(output_file, 'w', newline='') as file_out:
    reader = csv.reader(file_in)
    writer = csv.writer(file_out)

    # Write lines up to the start line directly
    for i, line in enumerate(reader):
        if i < start_line:
            writer.writerow(line)
        
        # Stop writing once the end line is reached
        if i >= end_line:
            break
