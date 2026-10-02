/* Representation fixture: never infer overlay eligibility from ownership. */
typedef unsigned char byte;
typedef unsigned int word;
__xdata volatile byte global;
static __xdata volatile byte file_static;
extern __xdata byte external;
__xdata byte * __xdata escaped;

static void touch(byte __xdata *p)
{
  escaped = p;
  global = *p;
}

byte foo(byte first, word second)
{
  volatile __xdata byte local;
  static __xdata byte retained;
  __xdata byte array[3];
  __xdata struct { byte a; word b; } aggregate;
  byte __xdata * volatile __xdata pointer;
  local = first;
  retained++;
  array[0] = local;
  aggregate.a = array[0];
  aggregate.b = second;
  pointer = array;
  touch(&first);
  touch(array);
  touch(&aggregate.a);
  file_static = pointer[0];
  return retained + aggregate.b;
}

byte bar(byte first)
{
  volatile __xdata byte local;
  local = first;
  touch(&first);
  return foo(local, 19);
}

byte sibling(byte first)
{
  volatile __xdata byte local;
  local = first;
  return local;
}

byte rent(byte first, byte second) __reentrant
{
  volatile byte local;
  static __xdata byte retained;
  local = first + second;
  retained++;
  return local + retained;
}

void interrupt_owner(void) __interrupt(1)
{
  volatile __xdata byte local;
  local = global;
  file_static = local;
}

__xdata byte external;
void main(void)
{
  global = bar(3) + rent(4, 5) + sibling(6);
}
