try {
    console.log(JSON.parse('{\\u0022a\\u0022: 1}'));
} catch (e) {
    console.log("Failed 1:", e.message);
}

try {
    console.log(JSON.parse('{"a": 1}'.replace(/\\u0022/g, '"')));
} catch (e) {
    console.log("Failed 2:", e.message);
}
