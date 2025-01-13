let idCounter = 0;

export function generateId() {
  idCounter++;
  const timestamp = Date.now();
  return `id-${timestamp}-${idCounter}`;
}
