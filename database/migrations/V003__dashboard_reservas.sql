BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.SREPI_Reservas_Log', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.SREPI_Reservas_Log (
            ID_Transaccion VARCHAR(50) NOT NULL,
            ID_Lote INT NOT NULL,
            Precio_Pagado DECIMAL(10, 2) NOT NULL,
            Fecha_Reserva DATETIME2(7) NOT NULL CONSTRAINT DF_SREPI_Reservas_Log_Fecha DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_SREPI_Reservas_Log PRIMARY KEY (ID_Transaccion),
            CONSTRAINT FK_SREPI_Reservas_Log_Lote FOREIGN KEY (ID_Lote) REFERENCES dbo.Inventario_Lotes(ID_Lote)
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
