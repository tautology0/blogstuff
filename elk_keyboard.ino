// Pins chosen, these are all on the back end of the Due
// I randomly chose them on how I wired the cable more than for anything else

// rst - linked directly to break, if this goes low break is pressed
const int rst    = 22;
// caps - the caps lock led, set this to low to turn on the LED
const int caps   = 23;
// the row of the matrix - read these
const int kbd[]  = { 24, 25, 26, 27 };
// the columns of the matrix, set these to LOW then read them
const int addr[] = { 28, 29, 30, 31, 32, 33, 39, 38, 36, 41, 40, 35, 34, 37 };

int rststate=0;
int c=0;

// The keyboard matrix
unsigned char matrix[][4] = {
  { 27, 1, 2, 3 },
  { '1', 'q', 'a', 'z' },
  { '2', 'w', 's', 'x' },
  { '3', 'e', 'd', 'c' },
  { '4', 'r', 'f', 'v' },
  { '5', 't', 'g', 'b' },
  { '6', 'y', 'h', 'n' },
  { '7', 'u', 'j', 'm' },
  { '8', 'i', 'k', ',' },
  { '9', 'o', 'l', '.' },
  { '0', 'p', ';', '/' },
  { '-', 4, ':', 0 },
  { 5, 6, 10, 7 },
  { 8, 9, 0, ' ' }
};

// Setup the pins
void setup() {
  Serial.begin(115200);
  pinMode(rst,  INPUT_PULLUP);
  rststate=1;
  pinMode(caps, OUTPUT);
  digitalWrite(caps, HIGH);
  for (int i = 0; i < 4; i++) {
    pinMode(kbd[i], INPUT_PULLUP);
  }
  for (int i = 0; i < 14; i++) {
    pinMode(addr[i], OUTPUT);
  }
}

// Scan for break being pressed returns 1 if break is pressed
int scan_break(void) {
  return (digitalRead(rst) == LOW)?1:0;
}

// scan for the row, returns one byte with the data lines in the lower nybble
// logic is inverted (i.e. 1 is LOW)
int scan_row(void) {
  int result=0;
  for (int j=0; j < 4; j++) {
    result += !digitalRead(kbd[j]) << j;
  }
  return result;
}

// Perform a full keyboard scan and print any pressed keys to serial
void scan_keyboard(void) {
  char output[256];
  int pressed;
  
  for (int i=0; i < 14;i++) {
    digitalWrite(addr[i], LOW);
    pressed=scan_row();
    digitalWrite(addr[i], HIGH);
    if (pressed > 0) {
      for (int j=0; j < 4; j++)
      {
        if ((pressed & (1<<j)) != 0) {
          //sprintf(output, "%c pressed (%d %d)\n", matrix[i][j], i, j);
          sprintf(output, "%c", matrix[i][j]);
          Serial.print(output);
        }
      }

    }
  }
}

// scan the keyboard
void loop() {
  delay(150);
  int h=-1,v=-1;
  char output[256];
  int rows[4];

  if (scan_break()) {
    Serial.print("Break Pressed\n");
  }
  scan_keyboard();
}
