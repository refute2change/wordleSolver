#read json
install.packages("jsonlite")
library(jsonlite)
data <- fromJSON("C:/Users/tvu50/Downloads/report/bfs_experiment_report.json")
str(data)

#convert to 1 table
library(dplyr)
df_result <- bind_rows(data, .id = "word") %>% 
  select(word, nodes_processed, time, wins, avg_time_per_guess, avg_time_per_game)
print(df_result)
summary(df_result)

#plot
library(tidyr)
library(ggplot2)
df_clean <- df_result %>% 
  distinct(word, .keep_all = TRUE)
cac_cot_can_ve <- c("nodes_processed", "time", "wins", "avg_time_per_guess", "avg_time_per_game")

ve_bieu_do <- function(ten_cot, y_min = NULL, y_max = NULL) {
  ggplot(df_clean, aes(x = reorder(word, -.data[[ten_cot]]), y = .data[[ten_cot]])) + 
    geom_col(fill = "darkcyan") + 
    coord_cartesian(ylim = c(y_min, y_max)) +
    labs(title = paste("Biểu đồ:", ten_cot), x = "Word", y = ten_cot) +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1, size = 8))
}

ve_bieu_do("nodes_processed", y_min = 3650, y_max = 4050)

# (Xem chán rồi thì bấm dòng dưới- này Gemini nó nói nha)
ve_bieu_do("time", y_min = 40, y_max = 90)

# (Tiếp tục...)
ve_bieu_do("wins", y_min = 2300, y_max = 2320)

ve_bieu_do("avg_time_per_guess")

ve_bieu_do("avg_time_per_game", y_min = 0.003, y_max=0.008)
