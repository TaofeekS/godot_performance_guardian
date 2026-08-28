class_name BenchmarkTestActor
extends Node2D

var actor_id: int = 0
var velocity := Vector2.ZERO
var accumulator: float = 0.0


func configure(new_actor_id: int, rng: RandomNumberGenerator) -> void:
	actor_id = new_actor_id
	position = Vector2(rng.randf_range(0.0, 640.0), rng.randf_range(0.0, 360.0))
	velocity = Vector2(rng.randf_range(-1.5, 1.5), rng.randf_range(-1.5, 1.5))
	queue_redraw()


func simulate_step(step_index: int) -> void:
	# A deterministic fixed-step update: benchmark work never depends on wall-clock delta.
	var phase := float((step_index + actor_id * 17) % 360) * 0.0174532925199433
	accumulator = fmod(accumulator + sin(phase) * 0.125 + cos(phase * 0.5) * 0.0625, 1024.0)
	position += velocity
	if position.x < 0.0 or position.x > 640.0:
		velocity.x = -velocity.x
		position.x = clampf(position.x, 0.0, 640.0)
	if position.y < 0.0 or position.y > 360.0:
		velocity.y = -velocity.y
		position.y = clampf(position.y, 0.0, 360.0)


func _draw() -> void:
	# Primitive-only art keeps the demo self-contained. Rendering is skipped headlessly.
	var color := Color.from_hsv(float(actor_id % 16) / 16.0, 0.65, 0.9)
	draw_circle(Vector2.ZERO, 3.0, color)

