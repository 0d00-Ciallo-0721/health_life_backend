import copy
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.diet.domains.tools.ai_service import AIService


class Command(BaseCommand):
    help = "Benchmark configured AI models for contest demo stability."

    def add_arguments(self, parser):
        parser.add_argument("--vision-models", default="", help="Comma-separated vision model names.")
        parser.add_argument("--text-models", default="", help="Comma-separated text model names.")
        parser.add_argument("--food-images", nargs="*", default=[], help="Food image paths for calorie recognition.")
        parser.add_argument("--ingredient-images", nargs="*", default=[], help="Ingredient image paths for fridge recognition.")

    def handle(self, *args, **options):
        original_config = copy.deepcopy(getattr(settings, "AI_CONFIG", {}))
        vision_models = self._option_models(options["vision_models"], "vision", original_config)
        text_models = self._option_models(options["text_models"], "text", original_config)

        rows = []
        for model in vision_models:
            rows.extend(self._run_vision_suite(model, options["food_images"], options["ingredient_images"], original_config))
        for model in text_models:
            rows.extend(self._run_text_suite(model, original_config))

        if not rows:
            self.stdout.write(self.style.WARNING("No AI benchmark cases ran. Provide model config and image paths."))
            return

        self.stdout.write("task_type,task_name,model,success,elapsed_ms,json_parsed,error")
        for row in rows:
            self.stdout.write(
                "{task_type},{task_name},{model},{success},{elapsed_ms},{json_parsed},{error}".format(**row)
            )

        best = self._best_model(rows)
        if best:
            self.stdout.write(self.style.SUCCESS(f"Recommended model by success and speed: {best}"))

    def _option_models(self, raw_value, task_type, original_config):
        models = [item.strip() for item in raw_value.split(",") if item.strip()]
        if models:
            return models
        model = original_config.get(task_type, {}).get("model")
        return [model] if model else []

    def _set_model(self, task_type, model_name, original_config):
        config = dict(original_config.get(task_type, {}))
        config["model"] = model_name
        settings.AI_CONFIG = dict(getattr(settings, "AI_CONFIG", {}))
        settings.AI_CONFIG[task_type] = config
        AIService._clients.pop(task_type, None)

    def _run_vision_suite(self, model, food_images, ingredient_images, original_config):
        self._set_model("vision", model, original_config)
        rows = []
        for path in food_images:
            rows.append(self._run_image_case("vision", "recognize_food", model, path, AIService.recognize_food))
        for path in ingredient_images:
            rows.append(self._run_image_case("vision", "recognize_ingredient", model, path, AIService.recognize_ingredient))
        return rows

    def _run_text_suite(self, model, original_config):
        self._set_model("text", model, original_config)
        questions = [
            "今天午餐吃了鸡胸肉和米饭，晚餐怎么搭配更适合减脂？",
            "运动后适合补充哪些食物？",
            "最近总是外卖，如何控制热量和盐分？",
        ]
        return [self._run_text_case("text", "ai_chat", model, question) for question in questions]

    def _run_image_case(self, task_type, task_name, model, path, func):
        started_at = time.perf_counter()
        try:
            with open(path, "rb") as image_file:
                result = func(image_file)
            success = "error" not in result
            return self._row(task_type, task_name, model, started_at, success, True, "" if success else result.get("error"))
        except Exception as exc:
            return self._row(task_type, task_name, model, started_at, False, False, exc)

    def _run_text_case(self, task_type, task_name, model, question):
        started_at = time.perf_counter()
        try:
            result = AIService.chat_with_ai(question)
            success = "error" not in result
            return self._row(task_type, task_name, model, started_at, success, None, "" if success else result.get("error"))
        except Exception as exc:
            return self._row(task_type, task_name, model, started_at, False, None, exc)

    def _row(self, task_type, task_name, model, started_at, success, json_parsed, error):
        return {
            "task_type": task_type,
            "task_name": task_name,
            "model": model,
            "success": int(bool(success)),
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "json_parsed": "" if json_parsed is None else int(bool(json_parsed)),
            "error": str(error).replace(",", " ")[:120] if error else "",
        }

    def _best_model(self, rows):
        grouped = {}
        for row in rows:
            bucket = grouped.setdefault(row["model"], {"success": 0, "count": 0, "elapsed": 0.0})
            bucket["success"] += int(row["success"])
            bucket["count"] += 1
            bucket["elapsed"] += float(row["elapsed_ms"])
        ranked = sorted(
            grouped.items(),
            key=lambda item: (item[1]["success"] / item[1]["count"], -item[1]["elapsed"] / item[1]["count"]),
            reverse=True,
        )
        return ranked[0][0] if ranked else None
