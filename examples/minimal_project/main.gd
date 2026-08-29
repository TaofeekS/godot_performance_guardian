extends Node2D

const ITEM_COUNT := 32
var positions: Array[Vector2] = []
var velocities: Array[Vector2] = []


func _ready() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1337
	for _index in ITEM_COUNT:
		positions.append(Vector2(rng.randf_range(20.0, 620.0), rng.randf_range(20.0, 340.0)))
		velocities.append(Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.0, 1.0)))
	queue_redraw()


func _process(_delta: float) -> void:
	for index in ITEM_COUNT:
		positions[index] += velocities[index]
		if positions[index].x < 10.0 or positions[index].x > 630.0:
			velocities[index].x = -velocities[index].x
		if positions[index].y < 10.0 or positions[index].y > 350.0:
			velocities[index].y = -velocities[index].y
	queue_redraw()


func _draw() -> void:
	for index in ITEM_COUNT:
		var color := Color.from_hsv(float(index) / ITEM_COUNT, 0.65, 0.9)
		draw_circle(positions[index], 4.0, color)

