BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('dbo.schema_version', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.schema_version (
            version VARCHAR(50) NOT NULL PRIMARY KEY,
            description VARCHAR(200) NOT NULL,
            installed_on DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME()
        );
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_version WHERE version = 'V001')
    BEGIN
        CREATE TABLE [dbo].[Categorias](
            [ID_Categoria] [int] IDENTITY(1,1) NOT NULL,
            [Nombre] [nvarchar](50) NOT NULL,
            [Multiplicador_XP] [decimal](3, 2) NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Categoria] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[Estados_Inventario](
            [ID_Estado_Inv] [tinyint] NOT NULL,
            [Nombre_Estado] [varchar](30) NOT NULL,
            [Descripcion] [varchar](100) NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Estado_Inv] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
        UNIQUE NONCLUSTERED
        (
            [Nombre_Estado] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[Estados_Reserva](
            [ID_Estado_Res] [tinyint] NOT NULL,
            [Nombre_Estado] [varchar](30) NOT NULL,
            [Descripcion] [varchar](100) NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Estado_Res] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
        UNIQUE NONCLUSTERED
        (
            [Nombre_Estado] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[Inventario_Lotes](
            [ID_Lote] [int] IDENTITY(1000,1) NOT NULL,
            [SKU] [varchar](20) NOT NULL,
            [ID_Estado_Inv] [tinyint] NOT NULL,
            [Fecha_Ingreso] [datetime2](7) NULL,
            [Fecha_Vencimiento] [datetime2](7) NOT NULL,
            [Cantidad_Inicial] [int] NOT NULL,
            [Cantidad_Disponible] [int] NOT NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Lote] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[Productos](
            [SKU] [varchar](20) NOT NULL,
            [ID_Categoria] [int] NOT NULL,
            [Nombre] [nvarchar](100) NOT NULL,
            [Precio_Base] [decimal](10, 2) NOT NULL,
            [Peso_Kg] [decimal](6, 3) NOT NULL,
            [Codigo_Barras] [varchar](50) NULL,
        PRIMARY KEY CLUSTERED
        (
            [SKU] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
        UNIQUE NONCLUSTERED
        (
            [Codigo_Barras] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[Registro_Retiros](
            [ID_Transaccion] [varchar](50) NOT NULL,
            [Telefono_Usuario] [varchar](20) NULL,
            [Fecha_Retiro] [datetime] NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Transaccion] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[SREPI_Ofertas_Activas](
            [ID_Oferta] [int] IDENTITY(1,1) NOT NULL,
            [ID_Lote] [int] NOT NULL,
            [Precio_DDA] [decimal](10, 2) NOT NULL,
            [XP_Otorgada] [int] NOT NULL,
            [Unidades_Disponibles] [int] NOT NULL,
            [Ultima_Actualizacion] [datetime2](7) NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Oferta] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[SREPI_Reservas](
            [ID_Reserva] [uniqueidentifier] NOT NULL,
            [Telefono_ID] [varchar](15) NOT NULL,
            [ID_Oferta] [int] NOT NULL,
            [ID_Estado_Res] [tinyint] NOT NULL,
            [Token_JWT] [varchar](500) NOT NULL,
            [Cantidad_Reservada] [int] NOT NULL,
            [Fecha_Reserva] [datetime2](7) NULL,
            [Fecha_Expiracion] [datetime2](7) NOT NULL,
            [Fecha_Retiro_Real] [datetime2](7) NULL,
        PRIMARY KEY CLUSTERED
        (
            [ID_Reserva] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE TABLE [dbo].[SREPI_Usuarios](
            [Telefono_ID] [varchar](15) NOT NULL,
            [Nombre] [nvarchar](50) NULL,
            [Nivel] [int] NULL,
            [XP_Acumulada] [int] NULL,
            [Fecha_Registro] [datetime2](7) NULL,
        PRIMARY KEY CLUSTERED
        (
            [Telefono_ID] ASC
        )WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
        ) ON [PRIMARY];

        CREATE NONCLUSTERED INDEX [IX_Inventario_FechaVencimiento] ON [dbo].[Inventario_Lotes]
        (
            [Fecha_Vencimiento] ASC
        )
        INCLUDE([SKU],[Cantidad_Disponible]) WITH (STATISTICS_NORECOMPUTE = OFF, DROP_EXISTING = OFF, ONLINE = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY];

        ALTER TABLE [dbo].[Categorias] ADD DEFAULT ((1.00)) FOR [Multiplicador_XP];
        ALTER TABLE [dbo].[Inventario_Lotes] ADD DEFAULT (sysutcdatetime()) FOR [Fecha_Ingreso];
        ALTER TABLE [dbo].[Registro_Retiros] ADD DEFAULT (getutcdate()) FOR [Fecha_Retiro];
        ALTER TABLE [dbo].[SREPI_Ofertas_Activas] ADD DEFAULT (sysutcdatetime()) FOR [Ultima_Actualizacion];
        ALTER TABLE [dbo].[SREPI_Reservas] ADD DEFAULT (newid()) FOR [ID_Reserva];
        ALTER TABLE [dbo].[SREPI_Reservas] ADD DEFAULT ((1)) FOR [Cantidad_Reservada];
        ALTER TABLE [dbo].[SREPI_Reservas] ADD DEFAULT (sysutcdatetime()) FOR [Fecha_Reserva];
        ALTER TABLE [dbo].[SREPI_Usuarios] ADD DEFAULT ((1)) FOR [Nivel];
        ALTER TABLE [dbo].[SREPI_Usuarios] ADD DEFAULT ((0)) FOR [XP_Acumulada];
        ALTER TABLE [dbo].[SREPI_Usuarios] ADD DEFAULT (sysutcdatetime()) FOR [Fecha_Registro];

        ALTER TABLE [dbo].[Inventario_Lotes] WITH CHECK ADD FOREIGN KEY([ID_Estado_Inv])
        REFERENCES [dbo].[Estados_Inventario] ([ID_Estado_Inv]);

        ALTER TABLE [dbo].[Inventario_Lotes] WITH CHECK ADD FOREIGN KEY([SKU])
        REFERENCES [dbo].[Productos] ([SKU]);

        ALTER TABLE [dbo].[Productos] WITH CHECK ADD FOREIGN KEY([ID_Categoria])
        REFERENCES [dbo].[Categorias] ([ID_Categoria]);

        ALTER TABLE [dbo].[SREPI_Ofertas_Activas] WITH CHECK ADD FOREIGN KEY([ID_Lote])
        REFERENCES [dbo].[Inventario_Lotes] ([ID_Lote]);

        ALTER TABLE [dbo].[SREPI_Reservas] WITH CHECK ADD FOREIGN KEY([ID_Estado_Res])
        REFERENCES [dbo].[Estados_Reserva] ([ID_Estado_Res]);

        ALTER TABLE [dbo].[SREPI_Reservas] WITH CHECK ADD FOREIGN KEY([ID_Oferta])
        REFERENCES [dbo].[SREPI_Ofertas_Activas] ([ID_Oferta]);

        ALTER TABLE [dbo].[SREPI_Reservas] WITH CHECK ADD FOREIGN KEY([Telefono_ID])
        REFERENCES [dbo].[SREPI_Usuarios] ([Telefono_ID]);

        ALTER TABLE [dbo].[Inventario_Lotes] WITH CHECK ADD CONSTRAINT [CHK_Cantidad] CHECK (([Cantidad_Disponible] >= (0)));
        ALTER TABLE [dbo].[Inventario_Lotes] CHECK CONSTRAINT [CHK_Cantidad];

        CREATE PROCEDURE [dbo].[sp_ObtenerLotesEnRiesgo]
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @HoraActual DATETIME2 = CAST(GETUTCDATE() AT TIME ZONE 'UTC' AT TIME ZONE 'SA Pacific Standard Time' AS DATETIME2);

            UPDATE Inventario_Lotes
            SET ID_Estado_Inv = 2
            WHERE ID_Estado_Inv = 1
              AND Cantidad_Disponible > 0
              AND DATEDIFF(DAY, @HoraActual, Fecha_Vencimiento) <= 15
              AND DATEDIFF(DAY, @HoraActual, Fecha_Vencimiento) > 0;

            SELECT
                L.ID_Lote,
                P.SKU,
                P.Nombre AS Nombre_Producto,
                C.Nombre AS Categoria,
                P.Precio_Base,
                C.Multiplicador_XP,
                L.Cantidad_Disponible,
                DATEDIFF(day, @HoraActual, L.Fecha_Vencimiento) AS DiasParaVencer
            FROM
                Inventario_Lotes L
            INNER JOIN
                Productos P ON L.SKU = P.SKU
            INNER JOIN
                Categorias C ON P.ID_Categoria = C.ID_Categoria
            INNER JOIN
                Estados_Inventario E ON L.ID_Estado_Inv = E.ID_Estado_Inv
            WHERE
                L.ID_Estado_Inv = 2
                AND L.Cantidad_Disponible > 0
                AND L.Fecha_Vencimiento > @HoraActual
            ORDER BY
                DiasParaVencer ASC;
        END;

        INSERT INTO dbo.schema_version (version, description)
        VALUES ('V001', 'Creacion de esquema inicial');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
